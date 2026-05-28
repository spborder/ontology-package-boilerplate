"""

Creating class objects from ontology

"""

import datetime
import os
import re
import shutil
from argparse import ArgumentParser
from string import Template

import owlready2
from tqdm import tqdm

from base_class.base_class import NewThing


def make_file_name(cls, label_property):
    class_label = getattr(cls, label_property, None)
    if isinstance(class_label, list):
        if len(class_label) > 0:
            class_label = class_label[0]
        else:
            # Backup label property is name
            class_label = cls.name
    elif class_label is None:
        class_label = cls.name

    cls_file_name = re.sub(r"\W+", "_", str(class_label))

    return cls_file_name


def make_class_file(
    cls, filepath, base_class, template, label_property, ontology_filepath, mode
):

    # Skipping RDF/S Classes
    if cls.name in ["Class", "Datatype", "Literal", "Property"]:
        return

    parent_imports = f"from ..{make_file_name(base_class, label_property)} import {make_file_name(base_class, label_property)}"

    cls_dict = {
        "ontology_file_path": ontology_filepath,
        "current_datetime": datetime.datetime.now(),
        "parent_imports": parent_imports,
        "property_imports": "",
        "class_name": make_file_name(cls, label_property),
        "base_class": str(make_file_name(base_class, label_property)),
        "docs": str(cls.isDefinedBy[0]) if len(cls.isDefinedBy) > 0 else "",
        "isDefinedBy": str(cls.isDefinedBy),
        "equivalent_to": f"[onto.get_namespace('{cls.namespace.base_iri}').{cls.name}]",
    }

    class_file = template.substitute(cls_dict)
    with open(filepath + ".py", mode) as f:
        f.write(class_file)
        f.close()


def make_class_dir(cls, filepath, clean):
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


def traverse_subclass(
    cls,
    dir_function,
    file_function,
    base_class,
    filepath,
    clean,
    template,
    label_property,
    ontology_filepath,
):

    cls_name = make_file_name(cls, label_property)
    filepath += os.sep + cls_name
    if len(list(cls.subclasses())) > 0:
        dir_function(cls, filepath, clean)
        file_function(
            cls,
            filepath + os.sep + cls_name,
            base_class,
            template,
            label_property,
            ontology_filepath,
            "w",
        )
        for subcls in cls.subclasses():
            if len(list(subcls.subclasses())) > 0:
                traverse_subclass(
                    subcls,
                    dir_function,
                    file_function,
                    cls,
                    filepath,
                    clean,
                    template,
                    label_property,
                    ontology_filepath,
                )
            else:
                append_template = Template(
                    "\n".join(template.template.splitlines()[19:] + ["", "", ""])
                )
                file_function(
                    subcls,
                    filepath + os.sep + cls_name,
                    cls,
                    append_template,
                    label_property,
                    ontology_filepath,
                    "a",
                )
    else:
        # If the path exists but clean is true, make the file,
        # If the path does not exist, make the file regardless of clean
        if not os.path.exists(filepath) or clean:
            file_function(
                cls,
                filepath,
                base_class,
                template,
                label_property,
                ontology_filepath,
                "w",
            )


def create(
    ontology_filepath: str,
    destination_path: str,
    scope: list | None = None,
    class_template: str = os.path.join(
        os.path.dirname(__file__), "templates", "class_template.txt"
    ),
    class_name_property: str = "label",
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
    param class_name_property: Property to use as the class name.
    type class_name_property: str
    param clean: Whether to replace all existing files in the destination directory or skip them.
    type clean: bool
    param verbose: Whether to print verbose output.
    type verbose: bool
    """
    ontology = owlready2.get_ontology(ontology_filepath).load()
    with ontology:
        base_class_obj = NewThing

    template = Template(open(class_template, "r").read())
    template.template = "\n".join(template.template.splitlines() + ["", "", ""])

    if scope is None:
        # With no specified scope, start from the child classes of owl:Thing
        thing_children = list(owlready2.Thing.subclasses())
    else:
        thing_children = scope

    with tqdm(thing_children) as pbar:
        for thing in thing_children:
            if thing is not base_class_obj:
                traverse_subclass(
                    thing,
                    make_class_dir,
                    make_class_file,
                    base_class_obj,
                    destination_path,
                    clean,
                    template,
                    class_name_property,
                    ontology_filepath,
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
        "scope", type=list, default=[], help="List of class names to get subclasses of"
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
        scope=args.scope,
        class_template=args.class_template,
        class_name_property=args.class_name_property,
        clean=args.clean,
        verbose=args.verbose,
    )
