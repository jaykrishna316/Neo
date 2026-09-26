def get_config():
    return {"db": "postgres"}

def process():
    config = get_config()
    return config

if __name__ == "__main__":
    print(process())
