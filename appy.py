import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Prakiraan Cuaca Wilayah Sulawesi Bagian Utara", layout="wide")

# Judul dan identitas
st.title("📡 Global Forecast System Viewer (Realtime via NOMADS)")
st.markdown("""
<div style='text-align: center; font-style: italic;'>
    <h4>oleh: Riri Ardhya Febriani</h4>
    <p>NPT: 14.24.0009 | Kelas: Meteorologi 8TB</p>
</div>
""", unsafe_allow_html=True)
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")

# Fungsi untuk load data
@st.cache_data(show_spinner=True)
def load_dataset(run_date, run_hour):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    try:
        ds = xr.open_dataset(base_url)
        return ds
    except Exception as e:
        st.error(f"Gagal membuka dataset dari NOMADS: {e}")
        return None

# Sidebar input
st.sidebar.title("⚙️ Pengaturan")
today = datetime.utcnow()
run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", today.date())
run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Jam ke depan", 0, 240, 0, step=1)
parameter = st.sidebar.selectbox("Parameter", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

if st.sidebar.button("🔎 Tampilkan Visualisasi"):
    ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
    if ds is None:
        st.stop()

    is_contour = False
    is_vector = False

    if "pratesfc" in parameter:
        var = ds["pratesfc"][forecast_hour, :, :] * 3600
        label = "Curah Hujan (mm/jam)"
        cmap = "Blues"
    elif "tmp2m" in parameter:
        var = ds["tmp2m"][forecast_hour, :, :] - 273.15
        label = "Suhu (°C)"
        cmap = "coolwarm"
    elif "ugrd10m" in parameter:
        u = ds["ugrd10m"][forecast_hour, :, :]
        v = ds["vgrd10m"][forecast_hour, :, :]
        speed = (u**2 + v**2)**0.5 * 1.94384
        var = speed
        label = "Kecepatan Angin (knot)"
        cmap = plt.cm.get_cmap("RdYlGn_r", 10)
        is_vector = True
    elif "prmsl" in parameter:
        var = ds["prmslmsl"][forecast_hour, :, :] / 100
        label = "Tekanan Permukaan Laut (hPa)"
        cmap = "cool"
        is_contour = True
    else:
        st.warning("Parameter tidak dikenali.")
        st.stop()

    # Subset wilayah Sulawesi Utara
    var = var.sel(lat=slice(-2, 4), lon=slice(118, 126))
    if is_vector:
        u = u.sel(lat=slice(-2, 4), lon=slice(118, 126))
        v = v.sel(lat=slice(-2, 4), lon=slice(118, 126))

    # Visualisasi menggunakan Cartopy
    fig = plt.figure(figsize=(10, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([118, 126, -2, 4], crs=ccrs.PlateCarree())

    # Format waktu
    try:
        valid_time = ds.time[forecast_hour].values
        valid_dt = pd.to_datetime(str(valid_time))
        valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    except:
        valid_str = f"t+{forecast_hour:03d}"

    tstr = f"t+{forecast_hour:03d}"
    ax.set_title(f"{label} - Valid {valid_str}", loc="left", fontsize=10, fontweight="bold")
    ax.set_title(f"GFS {tstr}", loc="right", fontsize=10, fontweight="bold")

    if is_contour:
        cs = ax.contour(var.lon, var.lat, var.values, levels=15, colors='black',
                        linewidths=0.8, transform=ccrs.PlateCarree())
        ax.clabel(cs, fmt="%d", colors='black', fontsize=8)
    else:
        im = ax.pcolormesh(var.lon, var.lat, var.values, cmap=cmap, transform=ccrs.PlateCarree())
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)
        if is_vector:
            ax.quiver(var.lon[::5], var.lat[::5], u.values[::5, ::5], v.values[::5, ::5],
                      transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

    # Kota-kota penting
    kota = {
        "Gorontalo": (0.537, 123.056),
        "Manado": (1.4748, 124.8421),
        "Palu": (-0.8917, 119.8707)
    }

    for nama, (lat, lon) in kota.items():
        ax.plot(lon, lat, marker='o', color='red', markersize=5, transform=ccrs.PlateCarree())
        ax.text(lon + 0.1, lat + 0.1, nama, transform=ccrs.PlateCarree(),
                fontsize=8, fontweight='bold', color='red')

    # Tambahan fitur geospasial
    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')

    st.pyplot(fig)
