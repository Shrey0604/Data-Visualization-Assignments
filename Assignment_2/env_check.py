"""Environment check for DAS732 A2 (Team Silica). Run: python env_check.py"""
import importlib, sys

PKGS = ["xarray", "netCDF4", "h5netcdf", "dask", "numpy", "pandas", "scipy", "matplotlib", "cartopy",
        "skimage", "imageio", "networkx", "community", "pyvis", "plotly", "joypy", "playwright", "tqdm"]

print("Python", sys.version.split()[0])
for name in PKGS:
    try:
        mod = importlib.import_module(name)
        print(f"  OK   {name:12s} {getattr(mod, '__version__', '')}")
    except Exception as exc:  # report and continue
        print(f"  FAIL {name:12s} {exc}")
import networkx as nx
print("networkx forceatlas2_layout:", hasattr(nx, "forceatlas2_layout"))
