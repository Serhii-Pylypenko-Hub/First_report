import uuid
import networkx as nx
import matplotlib.pyplot as plt


# --- Клас вузла та функції для побудови і візуалізації бінарного дерева ---
class Node:
    def __init__(self, key, color="#87CEEB"):  # світло-блакитний 
        self.left = None
        self.right = None
        self.val = key
        self.color = color
        self.id = str(uuid.uuid4())

def add_edges(graph, node, pos, x=0, y=0, layer=1):
    if node is not None:
        graph.add_node(node.id, color=node.color, label=str(node.val))
        if node.left:
            graph.add_edge(node.id, node.left.id)
            l = x - 1 / 2 ** layer
            pos[node.left.id] = (l, y - 1)
            add_edges(graph, node.left, pos, x=l, y=y - 1, layer=layer + 1)
        if node.right:
            graph.add_edge(node.id, node.right.id)
            r = x + 1 / 2 ** layer
            pos[node.right.id] = (r, y - 1)
            add_edges(graph, node.right, pos, x=r, y=y - 1, layer=layer + 1)
    return graph

def draw_tree(tree_root: Node, title: str = "Бінарне дерево"):
    tree = nx.DiGraph()
    pos = {tree_root.id: (0, 0)}
    add_edges(tree, tree_root, pos)

    colors = [node[1]['color'] for node in tree.nodes(data=True)]
    labels = {node[0]: node[1]['label'] for node in tree.nodes(data=True)}

    plt.figure(figsize=(8, 5))
    nx.draw(tree, pos=pos, labels=labels, arrows=False, node_size=2500, node_color=colors)
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

# --- Побудова вузлів дерева з масивного подання купи ---
def build_heap_tree(heap):
    if not heap:
        return None
    nodes = [Node(v) for v in heap]
    n = len(nodes)
    for i in range(n):
        li, ri = 2*i + 1, 2*i + 2
        if li < n:
            nodes[i].left = nodes[li]
        if ri < n:
            nodes[i].right = nodes[ri]
    return nodes[0]

# ----------  Демонстрація роботи ----------
def main():
    heap = [1, 3, 5, 7, 9, 8, 10, 12]
    root = build_heap_tree(heap)
    draw_tree(root, title="Бінарна купа (вузли з масиву)")

if __name__ == "__main__":
    main()
