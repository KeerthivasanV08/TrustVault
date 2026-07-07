from sklearn.preprocessing import LabelEncoder


def encode_column(series):
    le = LabelEncoder()
    return le.fit_transform(series.astype(str))