var grpc = require('grpc');

var protoDescriptor = grpc.load({root: __dirname+'/api', file:'cali/nlp/parsey_api.proto'});

var service = new protoDescriptor.cali.nlp.ParseyService("localhost:9000", grpc.credentials.createInsecure());

var conllIn = '1	내	내	NP	NP	_	0	_	_	_\n\
2	가	가	JKS	JKS	_	0	_	_	_\n\
3	집	집	NNG	NNG	_	0	_	_	_\n\
4	에	에	JKB	JKB	_	0	_	_	_\n\
5	가	가	VV	VV	_	0	_	_	_\n\
6	ㄴ다	ㄴ다	EF	EF	_	0	_	_	_\n\
7	.	.	SF	SF	_	0	_	_	_\n';

service.parse([conllIn], function(err, response) {
    console.log(JSON.stringify(response,null,'  '));
});
