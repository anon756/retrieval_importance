# retrieval_importance

Implementation and experimentation code for the submission _Improving Retrieval-Augmented Large Language Models with Data-Centric Refinement_ to NeurIPS'23.

## Implementation

We provide a Rust-based [implementation of the weight learning algorithm](https://github.com/anon756/retrieval_importance/blob/main/src/lib.rs) (callable from Python via pyo3) and several [helper functions](https://github.com/anon756/retrieval_importance/blob/main/python/retrieval_importance/utils.py). 

## Installation for development

 * Requires Python 3.9 and [Rust](https://www.rust-lang.org/tools/install) to be available
 
 1. Clone this repository
 1. Change to the project directory: `cd retrieval_importance`
 1. Create a virtualenv: `python3.9 -m venv venv`
 1. Activate the virtualenv `source venv/bin/activate`
 1. Install the dev dependencies with `pip install -r requirements-dev.txt`
 1. Build the project `maturin develop --release`
 
 * Optional steps:
    * Run the tests with `cargo test --release`
    * Run the benchmarks with `cargo bench`
    * Run the Python tests `python -m pytest`
    * Start jupyter with `jupyter notebook` and run the example notebooks
