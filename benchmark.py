import timeit
import random

def setup_data():
    return {f"key_{i}": random.random() for i in range(10000)}

def using_lambda(pair_vars):
    min_pair = min(pair_vars, key=lambda k: pair_vars[k])
    max_pair = max(pair_vars, key=lambda k: pair_vars[k])
    return min_pair, max_pair

def using_get(pair_vars):
    min_pair = min(pair_vars, key=pair_vars.get)
    max_pair = max(pair_vars, key=pair_vars.get)
    return min_pair, max_pair

if __name__ == "__main__":
    setup_code = "from __main__ import setup_data, using_lambda, using_get; pair_vars = setup_data()"

    print("Benchmarking lambda:")
    lambda_time = timeit.timeit("using_lambda(pair_vars)", setup=setup_code, number=1000)
    print(f"Lambda time: {lambda_time:.4f} seconds")

    print("Benchmarking get:")
    get_time = timeit.timeit("using_get(pair_vars)", setup=setup_code, number=1000)
    print(f"Get time: {get_time:.4f} seconds")

    print(f"Improvement: {(lambda_time - get_time) / lambda_time * 100:.2f}%")
