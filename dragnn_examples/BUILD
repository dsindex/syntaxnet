py_binary(
    name = "write_master_spec",
    srcs = ["write_master_spec.py", "model_dragnn.py"],
    deps = [":dragnn-deps"],
)

py_binary(
    name = "train_dragnn",
    srcs = ["train_dragnn.py", "model_dragnn.py"],
    deps = [":dragnn-deps"],
)

py_binary(
    name = "inference_dragnn",
    srcs = ["inference_dragnn.py", "model_dragnn.py"],
    deps = [":dragnn-deps"],
)

py_binary(
    name = "inference_dragnn_sejong",
    srcs = ["inference_dragnn_sejong.py", "model_dragnn.py"],
    deps = [":dragnn-deps"],
)

py_binary(
    name = "master_server",
    srcs = ["master_server.py"],
    deps = [":dragnn-deps"],
)

py_binary(
    name = "dragnn_dm",
    srcs = [
        "www/dragnn_dm.py",
        "www/handlers/base.py",
        "www/handlers/index.py",
        "model_dragnn.py",
    ],
    data = [
        ":log",
        ":static",
        ":templates"
    ],
    deps = [":dragnn-deps"],
)

filegroup(
    name = "log",
    data = glob(["www/log/*"]),
)

filegroup(
    name = "static",
    data = glob(["www/static/*/*"]),
)

filegroup(
    name = "templates",
    data = glob(["www/templates/*"]),
)

py_library(
    name = "dragnn-deps",
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
        "//syntaxnet:sentence_py_pb2",
        "@org_tensorflow//tensorflow:tensorflow_py",
        "@org_tensorflow//tensorflow/core:protos_all_py",
    ],
)

