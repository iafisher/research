import random
import sys
import time
from collections import Counter
from pathlib import Path
from xml.dom.minidom import Element, Text, parse as xmlparse

from lxml import etree


def filter_tagname(elements, tagname):
    return [e for e in elements if e.tagName == tagname]


def find_name(element):
    for child in element.childNodes:
        if (
            hasattr(child, "tagName")
            and child.tagName == "wikipediaArticleName_Canonical"
        ):
            assert len(child.childNodes) == 1 and isinstance(child.childNodes[0], Text)
            return child.childNodes[0].wholeText

    return None


# Downloaded from https://github.com/therohk/opencyc-kb
print("Parsing OWL file (this may take a little while)")
start = time.time()
# dom = xmlparse("opencyc-2012-05-10-readable.owl")
with open("opencyc-2012-05-10-readable.owl") as f:
    tree = etree.parse(f)
end = time.time()
print(f"Done parsing! ({end - start:.2f} s)")
print()

# elements = [e for e in dom.documentElement.childNodes if isinstance(e, Element)]
root = tree.getroot()
counter = Counter(e.tagName for e in root)
print("Most common:")
for name, count in counter.most_common(20):
    print(f"  {name}: {count:,}")

print()

singers = filter_tagname(root, "Singer")
print("Random singer:", find_name(random.choice(singers)))

cities = filter_tagname(root, "City")
print("Random city:", random.choice(cities).toxml())

classes = filter_tagname(root, "owl:Class")
print("Random class:", random.choice(classes).toxml())
