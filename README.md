# ontology-package-boilerplate

This is a utility for creating a Python package structure from an ontology file.

An example template is provided under "templates".

## Installation

This package can be installed using pip:
```bash
pip install ontology-package-boilerplate
```

The only two dependencies are `rdflib` and `tqdm`.

## Usage

This package was inspired by the concept of ontology-oriented-programming and the previous work done by Dr. Jean-Baptiste Lamy in [`owlready2`](http://owlready2.readthedocs.io).

While `owlready2` is a great tool for extending an ontology, this package was developed to provide an interface for adding functionality to terms in a fully developed ontology. Therefore, it does not implement a reasoner, facilitate SPARQL queries, enforce ontological constraints, or provide any built-in methods for working with ontologies.

`ontology-package-boilerplate` simply takes an ontology (readable as an rdflib `Graph`), and generates an class->subclass structure in the form of a Python package. This allows for terms to be imported along their hierarchical structure, provides an interface for detailed annotation of classes (through UI tools like Protégé), and for defining heritable methods for terms.
