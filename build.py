from pybind11.setup_helpers import Pybind11Extension, build_ext


def build(setup_kwargs):
    ext_modules = [
        Pybind11Extension(
            "eth_validator_watcher_ext", [
                "eth_validator_watcher/mod.cc"
            ],
            extra_compile_args=['-O3', '-pthread'],
            language='c++',
            cxx_std=17
        )
    ]
    setup_kwargs.update({
        "ext_modules": ext_modules,
        "cmd_class": {"build_ext": build_ext},
        "zip_safe": False,
    })
