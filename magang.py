import pandas as pd
import streamlit as st
import os
import sqlite3
from datetime import datetime

DB_FILE = "pengeluaran_kas.db"

# Fungsi koneksi DB
def get_connection():
    conn = sqlite3.connect(DB_FILE)
    return conn

# Fungsi buat tabel jika belum ada
def setup_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kas (
            id TEXT,
            tanggal TEXT,
            deskripsi_pekerjaan TEXT,
            deskripsi_pengeluaran TEXT,
            jumlah_barang INTEGER,
            unit TEXT,
            harga_per_satuan INTEGER,
            total_harga INTEGER,
            keterangan TEXT
        )
    """)
    conn.commit()
    conn.close()

# Fungsi untuk menghasilkan ID transaksi
def generate_id_transaksi(kode_pelanggan, tanggal, df):
    karakter_pertama = kode_pelanggan[0].upper() if kode_pelanggan else "X"
    karakter_kedua = "1"
    bulan_tahun = tanggal.strftime("%m%y")
    df_filtered = df[df['id'].str.startswith(karakter_pertama + karakter_kedua + bulan_tahun)]
    nomor_urut = len(df_filtered) + 1
    nomor_urut_str = f"{nomor_urut:03d}"
    return f"{karakter_pertama}{karakter_kedua}{bulan_tahun}{nomor_urut_str}"

# Fungsi konversi angka ke format Rupiah
def format_rupiah(x):
    try:
        return f"Rp {x:,.0f}".replace(",", ".")
    except:
        return x

# Fungsi ambil semua data dari DB
def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM kas", conn)
    df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')
    conn.close()
    return df

# Fungsi simpan data ke DB
def save_data(row):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO kas (id, tanggal, deskripsi_pekerjaan, deskripsi_pengeluaran,
                         jumlah_barang, unit, harga_per_satuan, total_harga, keterangan)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", row)
    conn.commit()
    conn.close()

# Fungsi hapus berdasarkan index di DataFrame
def delete_data_by_index(index):
    df = load_data()
    if index < len(df):
        id_to_delete = df.iloc[index]['id']
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kas WHERE id = ?", (id_to_delete,))
        conn.commit()
        conn.close()

# Fungsi update baris berdasarkan ID
def update_data_by_id(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE kas SET
            tanggal = ?,
            deskripsi_pekerjaan = ?,
            deskripsi_pengeluaran = ?,
            jumlah_barang = ?,
            unit = ?,
            harga_per_satuan = ?,
            total_harga = ?,
            keterangan = ?
        WHERE id = ?
    """, data)
    conn.commit()
    conn.close()

# Setup DB
setup_database()

# Streamlit config
st.set_page_config(page_title="Pengeluaran Kas", layout="wide")
st.sidebar.title("Navigasi")
menu = st.sidebar.radio("Pilih Halaman", ["Dashboard", "Input Data", "Data & Pencarian", "Kelola Data"])

# ====================== DASHBOARD ==========================
if menu == "Dashboard":
    st.title("\U0001F4CA Dashboard Pengeluaran")
    df = load_data()

    if not df.empty:
        total_harga = df['total_harga'].sum()
        avg_harga = df['total_harga'].mean()
        count = len(df)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Pengeluaran", f"Rp {total_harga:,.0f}".replace(",", "."))
        col2.metric("Rata-rata Pengeluaran", f"Rp {avg_harga:,.2f}".replace(",", ".").replace(".", ",", 1))
        col3.metric("Jumlah Transaksi", count)

        df['Bulan'] = df['tanggal'].dt.to_period('M').astype(str)
        monthly_summary = df.groupby('Bulan')['total_harga'].sum()
        st.line_chart(monthly_summary)
    else:
        st.warning("Belum ada data untuk ditampilkan.")

# ===================== INPUT DATA ==========================
elif menu == "Input Data":
    st.title("\U0001F4DD Input Pengeluaran Baru")

    df = load_data()
    kode_pelanggan = st.text_input("Kode Pelanggan", max_chars=10)
    tanggal = st.date_input("Tanggal", value=datetime.today())
    deskripsi_pekerjaan = st.text_area("Deskripsi Pekerjaan")
    deskripsi_pengeluaran = st.text_area("Deskripsi Pengeluaran")
    jumlah_barang = st.number_input("Jumlah Barang", min_value=1)
    unit = st.selectbox("Unit", ["pcs", "ea", "meter", "galon", "liter", "lot", "set", "assy", "kaleng", "pail", "unit", "lembar"])
    harga_per_satuan = st.number_input("Harga per Satuan (contoh: 1000000 untuk satu juta)", min_value=0)
    keterangan = st.text_input("Keterangan")
    total_harga = jumlah_barang * harga_per_satuan

    if st.button("Simpan Data"):
        if not kode_pelanggan:
            st.error("Kode Pelanggan harus diisi.")
        else:
            tanggal_str = tanggal.strftime("%d-%m-%Y")
            id_transaksi = generate_id_transaksi(kode_pelanggan, tanggal, df)
            row = (id_transaksi, tanggal_str, deskripsi_pekerjaan, deskripsi_pengeluaran,
                   jumlah_barang, unit, harga_per_satuan, total_harga, keterangan)
            save_data(row)
            st.success(f"Data ID {id_transaksi} berhasil disimpan!")

# =================== DATA & PENCARIAN ======================
elif menu == "Data & Pencarian":
    st.title("\U0001F50D Data & Pencarian")
    df = load_data()

    df_tampil = df.copy()
    df_tampil["harga_per_satuan"] = df_tampil["harga_per_satuan"].apply(format_rupiah)
    df_tampil["total_harga"] = df_tampil["total_harga"].apply(format_rupiah)
    df_tampil["tanggal"] = pd.to_datetime(df_tampil["tanggal"], errors='coerce').dt.strftime("%d-%m-%Y")

    st.dataframe(df_tampil)

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("\U0001F4E5 Unduh CSV", csv, "pengeluaran_kas.csv", "text/csv")

# ====================== KELOLA DATA ========================
elif menu == "Kelola Data":
    st.title("✏️ Kelola Data")
    df = load_data()

    if not df.empty:
        df_tampil = df.copy()
        df_tampil["harga_per_satuan"] = df_tampil["harga_per_satuan"].apply(format_rupiah)
        df_tampil["total_harga"] = df_tampil["total_harga"].apply(format_rupiah)
        df_tampil["tanggal"] = pd.to_datetime(df_tampil["tanggal"], errors='coerce').dt.strftime("%d-%m-%Y")

        st.dataframe(df_tampil)

        selected_index = st.number_input("Pilih Index untuk Edit/Hapus", min_value=0, max_value=len(df)-1, step=1)
        selected_row = df.iloc[selected_index]

        with st.expander("Edit Data Ini"):
            # Cek dan atasi NaT pada tanggal
            tanggal_value = selected_row['tanggal']
            if pd.isna(tanggal_value):
                tanggal_value = datetime.today()
            tanggal = st.date_input("Tanggal", value=tanggal_value)

            deskripsi_pekerjaan = st.text_input("Deskripsi Pekerjaan", value=selected_row['deskripsi_pekerjaan'])
            deskripsi_pengeluaran = st.text_input("Deskripsi Pengeluaran", value=selected_row['deskripsi_pengeluaran'])
            jumlah_barang = st.number_input("Jumlah Barang", min_value=1, value=int(selected_row['jumlah_barang']))
            unit = st.selectbox("Unit", [
                "pcs", "ea", "meter", "galon", "liter", "lot", "set",
                "assy", "kaleng", "pail", "unit", "lembar"
            ], index=[
                "pcs", "ea", "meter", "galon", "liter", "lot", "set",
                "assy", "kaleng", "pail", "unit", "lembar"
            ].index(selected_row['unit']))
            harga_per_satuan = st.number_input("Harga per Satuan", min_value=0, value=int(selected_row['harga_per_satuan']))
            keterangan = st.text_input("Keterangan", value=selected_row['keterangan'])
            total_harga = jumlah_barang * harga_per_satuan

            if st.button("Simpan Perubahan"):
                data = (
                    tanggal.strftime("%d-%m-%Y"), deskripsi_pekerjaan, deskripsi_pengeluaran,
                    jumlah_barang, unit, harga_per_satuan, total_harga, keterangan, selected_row['id']
                )
                update_data_by_id(data)
                st.success("Perubahan berhasil disimpan. Silakan refresh halaman.")

        if st.button("Hapus Data Ini"):
            delete_data_by_index(selected_index)
            st.success("Data berhasil dihapus. Silakan refresh halaman.")
    else:
        st.warning("Belum ada data.")

