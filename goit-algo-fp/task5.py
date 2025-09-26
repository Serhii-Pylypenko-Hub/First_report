from task4 import Node, draw_tree, build_heap_tree

# Градієнт HEX від темного до світлого
def hex_gradient(n, start="#0F2A4A", end="#9BD1FF"):
    def hex_to_rgb(h): return tuple(int(h[i:i+2], 16) for i in (1,3,5))
    def rgb_to_hex(t): return "#{:02X}{:02X}{:02X}".format(*t)
    s, e = hex_to_rgb(start), hex_to_rgb(end)
    out = []
    for i in range(max(1, n)):
        t = (i/(n-1)) if n > 1 else 0
        rgb = tuple(int(s[k] + (e[k]-s[k])*t) for k in range(3))
        out.append(rgb_to_hex(rgb))
    return out

# ІТЕРАЦІЙНИЙ DFS (СТЕК), БЕЗ РЕКУРСІЇ. Повертає список вузлів у порядку відвідування (Node).
def dfs_iter(root: Node):
    order = []
    stack = [root]
    visited_ids = set()
    while stack:
        v = stack.pop()
        if v.id in visited_ids:
            continue
        visited_ids.add(v.id)
        order.append(v)
        if v.right and v.right.id not in visited_ids:
            stack.append(v.right)
        if v.left and v.left.id not in visited_ids:
            stack.append(v.left)
    return order

# ІТЕРАЦІЙНИЙ BFS (ЧЕРГА). Повертає список вузлів у порядку відвідування (Node).
def bfs_iter(root: Node):
    order = []
    queue = [root]
    visited_ids = {root.id}
    while queue:
        v = queue.pop(0)
        order.append(v)
        if v.left and v.left.id not in visited_ids:
            visited_ids.add(v.left.id)
            queue.append(v.left)
        if v.right and v.right.id not in visited_ids:
            visited_ids.add(v.right.id)
            queue.append(v.right)
    return order

# Фарбуємо дерево за порядком обходу
def color_by_order(root: Node, order_nodes):
    palette = hex_gradient(len(order_nodes))
    for i, node in enumerate(order_nodes):
        node.color = palette[i]
 

# ----------  Демонстрація роботи ----------
def main():
    heap = [1, 3, 5, 7, 9, 8, 10, 12]
    root = build_heap_tree(heap)

    #  Початкове дерево
    dfs_order = dfs_iter(root)
    color_by_order(root, dfs_order)
    print("DFS порядок значень:", [n.val for n in dfs_order])
    draw_tree(root, title="DFS: кольори за порядком відвідування")

    #  BFS (черга): відновимо базовий колір і перерахуємо
    root = build_heap_tree(heap)
    bfs_order = bfs_iter(root)
    color_by_order(root, bfs_order)
    print("BFS порядок значень:", [n.val for n in bfs_order])
    draw_tree(root, title="BFS: кольори за порядком відвідування")

if __name__ == "__main__":
    main()
