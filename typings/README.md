# Type Stubs for C++ Libraries

This directory contains type stubs for third-party libraries that have C++ implementations with Python bindings but no official type hints.

## Purpose

These stubs enable static type checking with Pyright/mypy for libraries that would otherwise show import errors or lack type information.

## Libraries

### essentia (`essentia/__init__.pyi`)

Type stubs for essentia-tensorflow, an audio analysis library with C++ bindings.

**Website:** https://essentia.upf.edu/

**Installation:** `pip install essentia-tensorflow`

**Coverage:** This stub file covers only the subset of the Essentia API that is actually used by audiomancer:
- TensorFlow model predictors (TensorflowPredict, TensorflowPredict2D, etc.)
- Spectral analysis (Spectrum, Windowing, Centroid, RollOff, etc.)
- Rhythm analysis (RhythmExtractor2013)
- Tonal analysis (KeyExtractor, TuningFrequency, PitchSalience)

**Not covered:** The full Essentia API has 400+ algorithms. Only the ones we use are typed.

### faiss (`faiss/__init__.pyi`)

Type stubs for faiss-cpu, a library for efficient similarity search.

**Website:** https://github.com/facebookresearch/faiss

**Installation:** `pip install faiss-cpu`

**Coverage:** This stub file covers only the FAISS API used by audiomancer:
- IndexFlatIP (inner product index for cosine similarity)
- IndexFlatL2 (L2 distance index, included for completeness)
- write_index/read_index (serialization)

**Not covered:** FAISS has 50+ index types and many advanced features. Only basic functionality is typed.

## Usage

These stubs are automatically discovered by Pyright when the `typings/` directory is in the project root and `typeCheckingMode` is enabled in `pyproject.toml`.

No manual configuration is needed beyond:

```toml
[tool.pyright]
typeCheckingMode = "strict"
```

## Maintenance

If audiomancer starts using additional Essentia or FAISS APIs, update the corresponding stub files with the new signatures.

**Sources for type information:**
- Essentia documentation: https://essentia.upf.edu/reference/std_index.html
- FAISS documentation: https://github.com/facebookresearch/faiss/wiki
- Runtime inspection: `help(essentia.standard.ClassName)` in Python REPL
- Source code: Essentia and FAISS GitHub repositories

## Why Not Use typeshed?

These libraries are not in [typeshed](https://github.com/python/typeshed) (the official stub repository) because:
1. They are C++ libraries with Python bindings (complex to type comprehensively)
2. They have large APIs (400+ algorithms for Essentia, 50+ index types for FAISS)
3. Limited Python community usage compared to mainstream libraries

Project-specific stubs are the pragmatic solution for these niche scientific libraries.
