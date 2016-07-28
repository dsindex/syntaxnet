var grpc = require('grpc');

var protoDescriptor = grpc.load({root: __dirname+'/api', file:'cali/nlp/parsey_api.proto'});

var service = new protoDescriptor.cali.nlp.ParseyService("localhost:9000", grpc.credentials.createInsecure());

service.parse(["This is the first sentence", "I love this sentence"], function(err, response) {
	console.log(JSON.stringify(response,null,'  '));
});

