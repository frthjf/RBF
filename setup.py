#!/usr/bin/env python
if __name__ == "__main__":
    from setuptools import setup
    from setuptools.extension import Extension
    from Cython.Build import cythonize
    from pathlib import Path
    import subprocess as sp
    import numpy as np
    import json
    import re

    # this should create the file rbf/_version.py
    sp.call(['python', 'make_version.py'])
    version_file = Path('rbf/_version.py')
    version_text = version_file.read_text()
    version_info = dict(
        re.findall('(__[A-Za-z_]+__)\s*=\s*"([^"]+)"', version_text)
        )

    cy_ext = []
    cy_ext += [Extension(name="rbf.poly", sources=["rbf/poly.pyx"])]
    cy_ext += [Extension(name="rbf.sputils", sources=["rbf/sputils.pyx"])]
    cy_ext += [Extension(name="rbf.pde.halton", sources=["rbf/pde/halton.pyx"])]
    cy_ext += [Extension(name="rbf.pde.geometry", sources=["rbf/pde/geometry.pyx"])]
    cy_ext += [Extension(name="rbf.pde.sampling", sources=["rbf/pde/sampling.pyx"])]
    ext = cythonize(cy_ext)

    with open("rbf/_rbf_ufuncs/metadata.json", "r") as f:
        rbf_ufunc_metadata = json.load(f)

    for itm in rbf_ufunc_metadata:
        ext += [
            Extension(
                name=itm["module"],
                sources=itm["sources"],
                include_dirs=[np.get_include()],
            )
        ]

    setup(
        name="RBF",
        version="1.0",
        description="Package containing the tools necessary for radial basis "
        "function (RBF) applications",
        author="Trever Hines",
        author_email="treverhines@gmail.com",
        url="www.github.com/treverhines/RBF",
        packages=["rbf", "rbf.pde"],
        ext_modules=ext,
        include_package_data=True,
        license="MIT",
    )
