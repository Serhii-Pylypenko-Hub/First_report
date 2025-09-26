import heapq


# ----------  Алгоритм Дейкстри з пріоритетною чергою (heapq) ----------
def dijkstra(graph, start):
    try:
        dist = {v: float('inf') for v in graph}
        dist[start] = 0
        pq = [(0, start)]  
        visited = set()

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)

            for v, w in graph[u].items():
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))
        return dist
    except Exception as e:
        print(f"Помилка у dijkstra: {e}")
        return {}



# ----------  Невеликий приклад графа для демонстрації. ----------
def build_sample_graph():
    return {
        "A": {"B": 5, "C": 1},
        "B": {"A": 5, "C": 2, "D": 1},
        "C": {"A": 1, "B": 2, "D": 4, "E": 8},
        "D": {"B": 1, "C": 4, "E": 3, "F": 6},
        "E": {"C": 8, "D": 3},
        "F": {"D": 6},
    }

def main():
    g = build_sample_graph()
    s = "A"
    print("Граф:", g)
    print(f"Стартова вершина: {s}")
    result = dijkstra(g, s)
    print("Найкоротші відстані:", result)

if __name__ == "__main__":
    main()
