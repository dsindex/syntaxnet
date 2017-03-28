py_binary(
    name = "test_dragnn",
    srcs = ["test_dragnn.py"],
    data = [":data"],
    deps = [":test-dragnn-deps"],
)

py_library(
    name = "test-dragnn-deps",
    deps = [
        "//dragnn/core:dragnn_bulk_ops",
        "//dragnn/core:dragnn_ops",
        "//dragnn/protos:spec_py_pb2",
        "//dragnn/python:graph_builder",
        "//dragnn/python:lexicon",
        "//dragnn/python:load_dragnn_cc_impl_py",
        "//dragnn/python:spec_builder",
        "//dragnn/python:visualization",
		"//dragnn/python:sentence_io",
		"//dragnn/python:evaluation",
		"//dragnn/python:render_parse_tree_graphviz",
		"//dragnn/python:render_spec_with_graphviz",
		"//dragnn/python:trainer_lib",
        "//syntaxnet:load_parser_ops_py",
        "//syntaxnet:parser_ops",
        "//syntaxnet:sentence_py_pb2",
        "@org_tensorflow//tensorflow:tensorflow_py",
        "@org_tensorflow//tensorflow/core:protos_all_py",
    ],
)

