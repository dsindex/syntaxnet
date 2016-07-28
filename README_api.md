- how to run trained syntaxnet model using tensorflow serving?
  - see https://github.com/dmansfield/parsey-mcparseface-api/issues/1

- i copied parsey-mcparseface-api to api directory and modify little bit. and follow xtknight instructions.

- server
```bash
$ pwd
/path/to/models/syntaxnet/work

$ git clone --recurse-submodules https://github.com/tensorflow/serving

# you need to install gRPC properly
# https://tensorflow.github.io/serving/setup
# https://github.com/dsindex/tensorflow#tensorflow-serving

# apply patch by dmansfield to serving/tf_models/syntaxnet 
$ cd serving/tf_models
$ patch -p1 < ../../api/pr250-patch-a4b7bb9a.diff.txt
$ cd -

# configure serving/tensorflow
$ cd serving/tensorflow
$ ./configure
$ cd -

# modify serving/tensorflow_serving/workspace.bzl for referencing syntaxnet
$ cp api/modified_workspace.bzl serving/tensorflow_serving/workspace.bzl
$ cat api/modified_workspace.bzl
  ... 
  native.local_repository(
    name = "syntaxnet",
    path = workspace_dir + "/tf_models/syntaxnet",
  )
  ...

# append build instructions to serving/tensorflow_serving/example/BUILD
$ cat api/append_BUILD >> serving/tensorflow_serving/example/BUILD

# copy parsey_api.cc, parsey_api.proto to example directory to build
$ cp api/parsey_api* serving/tensorflow_serving/example/

# build parsey_api 
$ cd serving
$ bazel --output_user_root=bazel_root build --nocheck_visibility -c opt -s //tensorflow_serving/example:parsey_api --genrule_strategy=standalone --spawn_strategy=standalone --verbose_failures

# run parsey_api with exported model
$ ./bazel-bin/tensorflow_serving/example/parsey_api --port=9000 api/parsey_model
```

- node client
```bash
$ cd api/parsey_client
$ npm install

# if you have a trouble, check your version of node,npm
$ node --version
v4.4.7
$ npm --version
2.15.8
$ npm install grpc

# send sentences to parsey_api server
$ node index.js
{
  "result": [
    {
      "docid": "-:0",
      "text": "This is the first sentence",
      "token": [
        {
          "word": "This",
          "start": 0,
          "end": 3,
          "head": 4,
          "tag": "DT",
          "category": "DET",
          "label": "nsubj",
          "break_level": "SPACE_BREAK"
        },
...
}
```

- python client
```bash
# how to generate 'parsey_api_pb2.py'?
$ which grpc_python_plugin
# if this returns nothing, gRPC was not properly installed. see https://github.com/tensorflow/serving/issues/42
$ cd serving
$ protoc -I ./  --python_out=. --grpc_out=. --plugin=protoc-gen-grpc=`which grpc_python_plugin` ./tensorflow_serving/example/parsey_api.proto
$ cd ..

# copy parsey_client.py to serving/tensorflow_serving/example
# build it
$ cp api/parsey_client.py serving/tensorflow_serving/example
$ cd serving
$ bazel --output_user_root=bazel_root build --nocheck_visibility -c opt -s //tensorflow_serving/example:parsey_client --genrule_strategy=standalone --spawn_strategy=standalone --verbose_failures
$ ls bazel-bin/tensorflow_serving/example/parsey_client

# run
$ bazel-bin/tensorflow_serving/example/parsey_client --server=localhost:9000

```

- export model
```bash
# copy parsey_mcparseface.py to serving/tensorflow_serving/example
# buid it
$ cd ../
$ cp api/parsey_mcparseface.py serving/tensorflow_serving/example
$ cd serving
$ bazel --output_user_root=bazel_root build --nocheck_visibility -c opt -s //tensorflow_serving/example:parsey_mcparseface --genrule_strategy=standalone --spawn_strategy=standalone --verbose_failures
$ ls bazel-bin/tensorflow_serving/example/parsey_mcparseface

# run
# this will read model from --model_dir and export to --export_path directory
$ bazel-bin/tensorflow_serving/example/parsey_mcparseface --model_dir=syntaxnet/models/parsey_mcparseface --export_path=exported

```
