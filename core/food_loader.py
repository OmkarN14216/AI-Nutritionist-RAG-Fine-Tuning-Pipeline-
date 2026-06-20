import pandas as pd

class FoodDatabase:

    def __init__(self, csv_path="data/foods.csv"):
        self.df = pd.read_csv(csv_path)

    def get_all_foods(self):
        return self.df.to_dict(orient="records")