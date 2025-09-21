from typing import Optional

# ---- Вузол двійкового дерева  ----

class Node:
    def __init__(self, key: int):
        self.val: int = key
        self.left: Optional["Node"] = None
        self.right: Optional["Node"] = None

# ---- Вставка у BST для швидкого конструювання прикладів. ----

def bst_insert(root: Optional[Node], key: int) -> Node:
    try:
        if root is None:
            return Node(key)
        if key < root.val:
            root.left = bst_insert(root.left, key)
        else:
            root.right = bst_insert(root.right, key)
        return root
    except Exception as e:
        print(f"bst_insert error: {e}")
        return root

# ---- Сума всіх значень у дереві . ----

def sum_tree(root: Optional[Node]) -> int:
    try:
        if root is None:
            return 0
        total = 0
        stack = [root]
        while stack:
            node = stack.pop()
            if node is None:
                continue
            total += node.val
            if node.right: stack.append(node.right)
            if node.left:  stack.append(node.left)
        return total
    except Exception as e:
        print(f"sum_tree error: {e}")
        return 0

# ---- невеликий тест ----
if __name__ == "__main__":
    root = None
    for k in [10, 5, 15, 2, 7, 12, 20]:
        root = bst_insert(root, k)
    print("Сума очікується 71 ->", sum_tree(root))
    print("Сума (один елемент) 10 ->", sum_tree(Node(10)))
    print("Сума (порожнє) 0 ->", sum_tree(None))
