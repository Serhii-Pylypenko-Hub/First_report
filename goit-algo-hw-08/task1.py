from typing import Optional

# ---- Вузол двійкового дерева  ----

class Node:
    def __init__(self, key: int):
        self.val: int = key
        self.left: Optional["Node"] = None
        self.right: Optional["Node"] = None

    def __repr__(self) -> str:
        return f"Node({self.val})"
    
# ---- Вставка у BST  ----  

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
    

# ---- Пошук мінімального значення у BST/AVL. ---- 

def find_min_value(root: Optional[Node]) -> Optional[int]:
    try:
        if root is None:
            return None
        cur = root
        while cur.left:
            cur = cur.left
        return cur.val
    except Exception as e:
        print(f"find_min_value error: {e}")
        return None

# ---- невеликий тест ----
if __name__ == "__main__":
    root = None
    for k in [10, 5, 15, 2, 7, 12, 20]:
        root = bst_insert(root, k)

    print("Мінімум очікується 2 ->", find_min_value(root))
    print("Мінімум (один елемент) 10 ->", find_min_value(Node(10)))
    print("Мінімум (порожнє) None ->", find_min_value(None))
