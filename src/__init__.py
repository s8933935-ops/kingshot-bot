import warnings

# LightGBM 4.x の eval_set 内部非推奨警告をフィルタリング
warnings.filterwarnings("ignore", message=".*eval_set.*")
warnings.filterwarnings("ignore", message=".*Mean of empty slice.*")
