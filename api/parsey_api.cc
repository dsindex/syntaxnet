#include <algorithm>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "grpc++/security/server_credentials.h"
#include "grpc++/server.h"
#include "grpc++/server_builder.h"
#include "grpc++/server_context.h"
#include "grpc++/support/status.h"
#include "grpc++/support/status_code_enum.h"
#include "grpc/grpc.h"
#include "tensorflow/core/framework/tensor.h"
#include "tensorflow/core/framework/tensor_shape.h"
#include "tensorflow/core/framework/tensor_types.h"
#include "tensorflow/core/framework/types.pb.h"
#include "tensorflow/core/lib/core/status.h"
#include "tensorflow/core/lib/strings/strcat.h"
#include "tensorflow/core/platform/init_main.h"
#include "tensorflow/core/platform/logging.h"
#include "tensorflow/core/platform/types.h"
#include "tensorflow/core/public/session.h"
#include "tensorflow/core/public/session_options.h"
#include "tensorflow/core/util/command_line_flags.h"
#include "tensorflow_serving/example/parsey_api.grpc.pb.h"
#include "tensorflow_serving/example/parsey_api.pb.h"
#include "tensorflow_serving/servables/tensorflow/session_bundle_config.pb.h"
#include "tensorflow_serving/servables/tensorflow/session_bundle_factory.h"
#include "tensorflow/contrib/session_bundle/manifest.pb.h"
#include "tensorflow/contrib/session_bundle/session_bundle.h"
#include "tensorflow/contrib/session_bundle/signature.h"

#include "syntaxnet/sentence.pb.h"

using grpc::InsecureServerCredentials;
using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;
using grpc::StatusCode;
using tensorflow::serving::RegressionSignature;
using cali::nlp::ParseyRequest;
using cali::nlp::ParseyResponse;
using cali::nlp::ParseyService;
using tensorflow::serving::BatchingParameters;
using tensorflow::serving::SessionBundle;
using tensorflow::serving::SessionBundleConfig;
using tensorflow::serving::SessionBundleFactory;
using tensorflow::string;
using tensorflow::Tensor;
using tensorflow::TensorShape;
using syntaxnet::Sentence;

namespace {

// Creates a gRPC Status from a TensorFlow Status.
Status ToGRPCStatus(const tensorflow::Status& status) {
  return Status(static_cast<grpc::StatusCode>(status.code()),
                status.error_message());
}

class ParseyServiceImpl final : public ParseyService::Service {
 public:
  explicit ParseyServiceImpl(std::unique_ptr<SessionBundle> bundle)
      : bundle_(std::move(bundle)) {
    signature_status_ = tensorflow::serving::GetRegressionSignature(
        bundle_->meta_graph_def, &signature_);
  }

  Status Parse(ServerContext* context, const ParseyRequest* request,
                  ParseyResponse* response) override {

    if (request->text_size() == 0) {
      return Status(StatusCode::INVALID_ARGUMENT,
                    tensorflow::strings::StrCat("expected at least one string"));
    }

    int n = request->text_size();
    Tensor input(tensorflow::DT_STRING, {n});
    std::vector<Tensor> outputs;

    for (int i = 0; i < n; i++) {
      string t = request->text(i);
      if (t.length() == 0) {
	return Status(StatusCode::INVALID_ARGUMENT,
                      tensorflow::strings::StrCat("expected not empty string at index:",i));
      }
      LOG(INFO) << "received text:" <<i<<":"<< request->text(i);
      input.vec<string>()(i) = request->text(i);
    }

    LOG(INFO) << "input to tensor: " << signature_.input().tensor_name();

    const tensorflow::Status status1 = bundle_->session->Run(
      {{signature_.input().tensor_name(), input}}, // const std::vector< std::pair< string, Tensor > > &inputs
      {signature_.output().tensor_name()}, // const std::vector< string > &output_tensor_names
      {}, // const std::vector< string > &target_node_names
      &outputs
      );

    LOG(INFO) << "ran session once " << status1 << " " << outputs.size() << " output tensors available";
    auto documents = outputs[0].vec<string>();
    LOG(INFO) << "documents size: " << documents.size();
    
    for (int i = 0; i < documents.size(); ++i) {
      Sentence *sentence = response->add_result();
      sentence->ParseFromString(documents(i));
      LOG(INFO) << "document " << i << ": "<< sentence->DebugString();
    }

    return Status::OK;
  }

 private:
  std::unique_ptr<SessionBundle> bundle_;
  tensorflow::Status signature_status_;
  RegressionSignature signature_;
};

void RunServer(int port, std::unique_ptr<SessionBundle> bundle) {
  // "0.0.0.0" is the way to listen on localhost in gRPC.
  const string server_address = "0.0.0.0:" + std::to_string(port);
  ParseyServiceImpl service(std::move(bundle));
  ServerBuilder builder;
  std::shared_ptr<grpc::ServerCredentials> creds = InsecureServerCredentials();
  builder.AddListeningPort(server_address, creds);
  builder.RegisterService(&service);
  std::unique_ptr<Server> server(builder.BuildAndStart());
  LOG(INFO) << "Running...";
  server->Wait();
}

}  // namespace

int main(int argc, char** argv) {
  tensorflow::int32 port = 0;
  const bool parse_result =
      tensorflow::ParseFlags(&argc, argv, {tensorflow::Flag("port", &port)});
  if (!parse_result) {
    LOG(FATAL) << "Error parsing command line flags.";
  }

  if (argc != 2) {
    LOG(FATAL) << "Usage: parsey_api --port=9000 /path/to/export";
  }
  const string bundle_path(argv[1]);

  tensorflow::port::InitMain(argv[0], &argc, &argv);

  SessionBundleConfig session_bundle_config;

  //////
  // Request batching, keeping default values for the tuning parameters.
  //
  // (If you prefer to disable batching, simply omit the following lines of code
  // such that session_bundle_config.batching_parameters remains unset.)
  BatchingParameters* batching_parameters =
      session_bundle_config.mutable_batching_parameters();
  batching_parameters->mutable_thread_pool_name()->set_value(
      "parsey_service_batch_threads");
  // Use a very large queue, to avoid rejecting requests. (Note: a production
  // server with load balancing may want to use the default, much smaller,
  // value.)
  batching_parameters->mutable_max_enqueued_batches()->set_value(1000);
  //////

  std::unique_ptr<SessionBundleFactory> bundle_factory;

  TF_QCHECK_OK(
      SessionBundleFactory::Create(session_bundle_config, &bundle_factory));

  std::unique_ptr<SessionBundle> bundle(new SessionBundle);
  TF_QCHECK_OK(bundle_factory->CreateSessionBundle(bundle_path, &bundle));

  RunServer(port, std::move(bundle));

  return 0;
}
