import os


# Automated tests opt into deterministic fixtures explicitly. Production and
# ordinary local startup default to public Binance market data.
os.environ.setdefault("APP_MODE", "simulation")
