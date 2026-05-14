memory = []

def save_memory(query, final, score):
    memory.append({
        "query": query,
        "final": final,
        "score": score
    })

def get_memory():
    return memory