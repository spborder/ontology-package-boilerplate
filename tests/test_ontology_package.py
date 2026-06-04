"""

Testing out package creation using simple ontology

"""

import os
import sys

sys.path.append("src/")
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from ontology_package_boilerplate import create

ontology_path = os.path.join(os.path.dirname(__file__), "pizza.owl")
destination_path = os.path.join(os.path.dirname(__file__), "output") + os.sep


def test():
    ontology_path = "/home/sam/Desktop/Pathology_Image_Feature_Ontology/pathology-image-features/src/pathology_image_features/ontology/pifo.owl"
    print(os.path.exists(ontology_path))

    graph = Graph().parse(ontology_path)
    print(len(graph))
    print(
        f"Number of classes: {len(list(graph.subjects(predicate=RDF.type, object=OWL.Class)))}"
    )
    base_classes = []
    for cls in graph.subjects(predicate=RDF.type, object=OWL.Class):
        if not isinstance(cls, BNode) and not cls == OWL.Restriction:
            bases = list(graph.objects(subject=cls, predicate=RDFS.subClassOf))
            if len(bases) == 0:
                eq_to = list(graph.objects(subject=cls, predicate=OWL.equivalentClass))
                if len(eq_to) == 0:
                    base_classes.append(cls)

    base_classes = list(set(base_classes))

    print(f"Base classes: {base_classes=}")
    for b in base_classes:
        print(list(graph.subjects(predicate=RDFS.subClassOf, object=b)))


def main():

    create(
        ontology_filepath=ontology_path,
        destination_path=destination_path,
        clean=True,
        verbose=True,
    )


if __name__ == "__main__":
    # test()
    main()
