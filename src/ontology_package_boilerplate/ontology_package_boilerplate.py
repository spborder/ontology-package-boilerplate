"""

Creating class objects from ontology

"""

import datetime
import os
import re
import shutil
from argparse import ArgumentParser
from collections import namedtuple
from string import Template

from rdflib import BNode, Graph
from rdflib.namespace import OWL, RDF, RDFS
from tqdm import tqdm

from .base_class import Thing

URI_REGEX_SPLIT = r"[^a-zA-Z\d\s:_]"


def traverse_subclass(
    cls,
    class_maker,
    base_class,
    filepath,
    clean,
):
    cls_object = class_maker.make_class_object(cls)
    cls_name = cls_object.filename

    filepath += os.sep + cls_name
    if len(cls_object.subclasses) > 0:
        class_maker.make_class_dir(filepath, clean)
        class_maker.make_class_file(
            cls_object,
            filepath + os.sep + cls_name,
            base_class,
            "w",
        )
        for subcls in cls_object.subclasses:
            subcls_object = class_maker.make_class_object(subcls)
            if len(subcls_object.subclasses) > 0:
                traverse_subclass(
                    subcls,
                    class_maker,
                    cls_object,
                    filepath,
                    clean,
                )
            else:
                class_maker.make_class_file(
                    subcls_object,
                    filepath + os.sep + cls_name,
                    cls_object,
                    "a",
                )
    else:
        # If the path exists but clean is true, make the file,
        # If the path does not exist, make the file regardless of clean
        if not os.path.exists(filepath) or clean:
            class_maker.make_class_file(
                cls_object,
                filepath,
                base_class,
                "w",
            )


ClassObject = namedtuple(
    "ClassObject", ["iri", "name", "filename", "subclasses", "label", "isDefinedBy"]
)


class ClassObjectMaker(Graph):
    def __init__(
        self,
        ontology_filepath,
        destination_path,
        class_template,
        template_header_lines,
        class_name_property,
    ):
        super().__init__()
        self.ontology_filepath = ontology_filepath
        self.destination_path = destination_path
        self.class_template = class_template
        self.template_header_lines = template_header_lines
        self.class_name_property = class_name_property

        self.parse(self.ontology_filepath)

    def get_base_classes(self, scope=[]):

        base_classes = []
        if len(scope) == 0:
            # With no specified scope, find classes which are not the subclass of anything
            if (
                len(list(self.subjects(predicate=RDFS.subClassOf, object=OWL.Thing)))
                > 0
            ):
                # Or subclasses of OWL:Thing
                base_classes = list(
                    self.subjects(predicate=RDFS.subClassOf, object=OWL.Thing)
                )
            else:
                for cls in self.subjects(predicate=RDF.type, object=OWL.Class):
                    if not isinstance(cls, BNode) and not cls == OWL.Restriction:
                        bases = list(
                            self.objects(subject=cls, predicate=RDFS.subClassOf)
                        )
                        if len(bases) == 0:
                            eq_to = list(
                                self.objects(subject=cls, predicate=OWL.equivalentClass)
                            )
                            if len(eq_to) == 0:
                                base_classes.append(cls)

        else:
            base_classes = scope

        return base_classes

    def make_class_object(self, uri):
        attrs = {}
        for prop in [RDFS.label, RDFS.isDefinedBy]:
            value = list(self.objects(subject=uri, predicate=prop))
            prop_name = re.split(URI_REGEX_SPLIT, str(prop))[-1]
            attrs[prop_name] = [v.toPython() for v in value]

        cls_name = self.value(subject=uri, predicate=self.class_name_property)
        if cls_name is None:
            cls_name = re.split(URI_REGEX_SPLIT, (uri))[-1]

        cls_name = self.make_file_name(cls_name)

        subclasses = list(self.subjects(predicate=RDFS.subClassOf, object=uri))

        cls_obj = ClassObject(
            iri=uri,
            name=cls_name,
            filename=cls_name,
            label=attrs.get("label"),
            isDefinedBy=attrs.get("isDefinedBy"),
            subclasses=subclasses,
        )

        return cls_obj

    def make_file_name(self, cls_name):
        cls_file_name = re.sub(r"\W+", "_", str(cls_name))
        return cls_file_name

    def make_class_dir(self, filepath, clean):
        class_dir_path = os.path.join(filepath)
        if not os.path.exists(class_dir_path):
            os.makedirs(class_dir_path)
        else:
            if clean:
                shutil.rmtree(class_dir_path)
                os.makedirs(class_dir_path)

        init_path = os.path.join(class_dir_path, "__init__.py")
        if not os.path.exists(init_path) or clean:
            open(init_path, "w")

    def make_class_file(self, cls_object, filepath, base_class, mode):
        # Skipping RDF/S Classes
        if cls_object.name in ["Class", "Datatype", "Literal", "Property"]:
            return

        parent_imports = f"from ..{base_class.filename} import {base_class.filename}"

        cls_dict = {
            "ontology_file_path": self.ontology_filepath,
            "current_datetime": datetime.datetime.now(),
            "parent_imports": parent_imports,
            "property_imports": "",
            "class_name": cls_object.name,
            "label": cls_object.label,
            "iri": str(cls_object.iri),
            "base_class": base_class.name,
            "docs": str(cls_object.isDefinedBy),
            "isDefinedBy": str(cls_object.isDefinedBy),
        }

        if mode == "w":
            template = self.class_template
        else:
            template = Template(
                "\n".join(
                    self.class_template.template.splitlines()[
                        self.template_header_lines :
                    ]
                    + ["", "", ""]
                )
            )

        cls_file = template.substitute(cls_dict)
        with open(filepath + ".py", mode) as f:
            f.write(cls_file)
            f.close()


def create(
    ontology_filepath: str,
    destination_path: str,
    base_class_obj=Thing,
    scope: list = [],
    class_template: str = os.path.join(
        os.path.dirname(__file__), "templates", "class_template.txt"
    ),
    template_header_lines: int | None = None,
    class_name_property=RDFS.label,
    clean: bool = False,
    verbose: bool = True,
):
    """
    Create a package structure from an ontology file.

    param ontology_filepath: Path to the ontology file.
    type ontology_filepath: str
    param destination_path: Path to the package destination directory.
    type destination_path: str
    param scope: List of class names to get subclasses of
    type scope: list | None
    param class_template: Path to the class template file.
    type class_template: str
    param template_header_lines: Number of lines to skip when appending to a class file. If not provided, the line containing the last import statement will be used.
    type template_header_lines: int | None
    param class_name_property: Property to use as the class name.
    type class_name_property: str
    param clean: Whether to replace all existing files in the destination directory or skip them.
    type clean: bool
    param verbose: Whether to print verbose output.
    type verbose: bool
    """
    if base_class_obj is not Thing:
        assert class_template != os.path.join(
            os.path.dirname(__file__), "templates", "class_template.txt"
        ), "You must provide a new class template when setting a custom base class"

    template = Template(open(class_template, "r").read())
    template.template = "\n".join(template.template.splitlines() + ["", "", ""])

    if template_header_lines is None:
        template_lines = open(class_template, "r").readlines()
        import_line_idx = [
            idx for idx, line in enumerate(template_lines) if "import" in line
        ]
        template_header_lines = import_line_idx[-1]

    class_object_maker = ClassObjectMaker(
        ontology_filepath=ontology_filepath,
        destination_path=destination_path,
        class_template=template,
        template_header_lines=template_header_lines,
        class_name_property=class_name_property,
    )

    base_classes = class_object_maker.get_base_classes(scope)
    base_class_class_obj = ClassObject(
        iri=getattr(base_class_obj, "iri", ""),
        name=base_class_obj.__name__,
        filename=base_class_obj.__name__,
        label=getattr(base_class_obj, "label", base_class_obj.__name__),
        isDefinedBy=getattr(base_class_obj, "isDefinedBy", base_class_obj.__doc__),
        subclasses=[],
    )

    with tqdm(base_classes) as pbar:
        for thing in base_classes:
            traverse_subclass(
                thing,
                class_object_maker,
                base_class_class_obj,
                destination_path,
                clean,
            )
            if verbose:
                pbar.update(1)


if __name__ == "__main__":
    parser = ArgumentParser(
        prog="ontology-package-boilerplate",
        description="Create a Python package from an ontology file.",
    )
    parser.add_argument("ontology_filepath", type=str, help="Path to the ontology file")
    parser.add_argument(
        "destination_path", type=str, help="Path to the destination directory"
    )
    parser.add_argument(
        "class_template",
        default=os.path.join(
            os.path.dirname(__file__), "templates", "class_template.txt"
        ),
        type=str,
        help="Path to the class template file",
    )
    parser.add_argument(
        "class_name_property",
        type=str,
        default="label",
        help="Property to use as the class name",
    )
    parser.add_argument(
        "clean",
        type=bool,
        default=False,
        help="Whether to replace all existing files in the destination directory or skip them.",
    )
    parser.add_argument(
        "verbose", type=bool, default=True, help="Whether to print verbose output."
    )
    args = parser.parse_args()

    create(
        ontology_filepath=args.ontology_filepath,
        destination_path=args.destination_path,
        class_template=args.class_template,
        class_name_property=args.class_name_property,
        clean=args.clean,
        verbose=args.verbose,
    )
