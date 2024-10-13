def expose_for_llm(func):
    func.expose_for_llm = True
    return func
