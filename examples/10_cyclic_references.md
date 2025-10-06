# Cyclic References

Cyclic and self-referencing structures in marshmallow-recipe.

## Forward References with Quotes

Use quoted type hints for forward references:

```python
import dataclasses

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TreeNode:
    """Tree node with optional parent reference (cyclic)."""

    id: int
    name: str
    parent: "TreeNode | None" = None  # Forward reference with quotes
```

## Cyclic References (Parent-Child)

Parent-child relationships work seamlessly:

```python
# Tree structure with parent references
root = TreeNode(id=1, name="root", parent=None)
child1 = TreeNode(id=2, name="child1", parent=root)
child2 = TreeNode(id=3, name="child2", parent=root)
grandchild = TreeNode(id=4, name="grandchild", parent=child1)

# Serialise child with parent reference
child_dict = mr.dump(grandchild)
# {
#     'id': 4,
#     'name': 'grandchild',
#     'parent': {
#         'id': 2,
#         'name': 'child1',
#         'parent': {
#             'id': 1,
#             'name': 'root'
#         }
#     }
# }

# Deserialise back
loaded_grandchild = mr.load(TreeNode, child_dict)
# loaded_grandchild.name == "grandchild"
# loaded_grandchild.parent.name == "child1"
# loaded_grandchild.parent.parent.name == "root"
```

## Self-Referencing Lists

Lists of the same type (comment trees, folder hierarchies):

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Comment:
    """Comment with replies (self-referencing list)."""

    id: int
    text: str
    author: str
    replies: list["Comment"] = dataclasses.field(default_factory=list)  # Self-referencing


# Comment thread with nested replies
main_comment = Comment(
    id=1,
    text="Main comment",
    author="Alice",
    replies=[
        Comment(
            id=2,
            text="Reply to main",
            author="Bob",
            replies=[
                Comment(id=4, text="Nested reply", author="Dave", replies=[]),
            ],
        ),
        Comment(id=3, text="Another reply", author="Charlie", replies=[]),
    ],
)

# Serialise comment tree
comment_dict = mr.dump(main_comment)
# {
#     'id': 1,
#     'text': 'Main comment',
#     'author': 'Alice',
#     'replies': [
#         {
#             'id': 2,
#             'text': 'Reply to main',
#             'author': 'Bob',
#             'replies': [
#                 {'id': 4, 'text': 'Nested reply', 'author': 'Dave', 'replies': []}
#             ]
#         },
#         {'id': 3, 'text': 'Another reply', 'author': 'Charlie', 'replies': []}
#     ]
# }

# Deserialise back
loaded_comment = mr.load(Comment, comment_dict)
# len(loaded_comment.replies) == 2
# len(loaded_comment.replies[0].replies) == 1
# loaded_comment.replies[0].replies[0].author == "Dave"
```

## Folder Hierarchies

Self-referencing structures like folder trees:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Folder:
    """Folder that can contain subfolders (self-referencing)."""

    name: str
    subfolders: list["Folder"] = dataclasses.field(default_factory=list)
    file_count: int = 0


# Folder structure
documents = Folder(
    name="Documents",
    file_count=5,
    subfolders=[
        Folder(
            name="Work",
            file_count=10,
            subfolders=[
                Folder(name="Projects", file_count=20, subfolders=[]),
                Folder(name="Reports", file_count=15, subfolders=[]),
            ],
        ),
        Folder(name="Personal", file_count=8, subfolders=[]),
    ],
)

# Serialise folder hierarchy
folder_dict = mr.dump(documents)
# {
#     'name': 'Documents',
#     'file_count': 5,
#     'subfolders': [
#         {
#             'name': 'Work',
#             'file_count': 10,
#             'subfolders': [
#                 {'name': 'Projects', 'file_count': 20, 'subfolders': []},
#                 {'name': 'Reports', 'file_count': 15, 'subfolders': []}
#             ]
#         },
#         {'name': 'Personal', 'file_count': 8, 'subfolders': []}
#     ]
# }

# Deserialise back
loaded_folders = mr.load(Folder, folder_dict)
# len(loaded_folders.subfolders) == 2
# len(loaded_folders.subfolders[0].subfolders) == 2
```

## Deep Nesting

Deep nesting is handled correctly:

```python
# Create deeply nested structure (10 levels)
deep_comment = Comment(id=1, text="Level 1", author="User1", replies=[])
current = deep_comment
for i in range(2, 11):
    nested = Comment(id=i, text=f"Level {i}", author=f"User{i}", replies=[])
    current.replies = [nested]
    current = nested

# Serialise and deserialise deep nesting
deep_dict = mr.dump(deep_comment)
loaded_deep = mr.load(Comment, deep_dict)

# Verify depth
depth = 0
current = loaded_deep
while current.replies:
    depth += 1
    current = current.replies[0]

# depth == 9 (10 levels total)
```

## Use Cases

Common use cases for cyclic references:

- **Comment threads** - Reddit-style nested comments
- **Folder hierarchies** - File system structures
- **Organisation charts** - Employee-manager relationships
- **Category trees** - Nested product categories
- **Menu structures** - Nested navigation menus
- **Graph nodes** - Connected node structures

## Important Notes

1. **Use quotes** for forward references: `"ClassName"` or `list["ClassName"]`
2. **Optional parent** references: `parent: "TreeNode | None" = None`
3. **Default factories** for lists: `replies: list["Comment"] = dataclasses.field(default_factory=list)`
4. **Deep nesting** is supported with no practical limit
5. **Round-trip serialisation** preserves structure completely
