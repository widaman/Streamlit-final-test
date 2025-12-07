# Dashboard Analisis Saham dengan Streamlit
# Aplikasi untuk menganalisis data saham secara real-time

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import ta

# Konstanta kurs USD ke IDR (bisa diupdate secara real-time)
KURS_USD_IDR = 15700  # Default rate, akan diupdate secara otomatis

##########################################################################################
## BAGIAN 1: Fungsi-fungsi untuk Mengambil dan Memproses Data Saham ##
##########################################################################################

# Fungsi untuk mendapatkan kurs USD/IDR terkini
@st.cache_data(ttl=300)  # Cache selama 5 menit
def ambil_kurs_usd_idr():
    """
    Mengambil kurs USD/IDR real-time dari Yahoo Finance
    """
    try:
        kurs_data = yf.download('IDR=X', period='1d', interval='1m', progress=False)
        if not kurs_data.empty:
            if isinstance(kurs_data.columns, pd.MultiIndex):
                kurs_data.columns = kurs_data.columns.get_level_values(0)
            return kurs_data['Close'].iloc[-1]
        else:
            return KURS_USD_IDR  # fallback ke default
    except:
        return KURS_USD_IDR  # fallback ke default

# Mengambil data saham dari Yahoo Finance
def ambil_data_saham(simbol, periode, interval):
    """
    Fungsi untuk mengunduh data historis saham
    Parameter:
        simbol: kode ticker saham
        periode: rentang waktu data
        interval: interval waktu per data point
    """
    tanggal_akhir = datetime.now()
    
    if periode == '1minggu':
        tanggal_awal = tanggal_akhir - timedelta(days=7)
        data_saham = yf.download(simbol, start=tanggal_awal, end=tanggal_akhir, interval=interval, progress=False)
    else:
        data_saham = yf.download(simbol, period=periode, interval=interval, progress=False)
    
    return data_saham

# Memproses dan membersihkan data
def olah_data(df):
    """
    Mengkonversi data ke timezone yang sesuai dan format yang benar
    """
    # Flatten multi-level columns if they exist
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Ensure we have the right columns
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    
    if df.index.tzinfo is None:
        df.index = df.index.tz_localize('UTC')
    
    df.index = df.index.tz_convert('US/Eastern')
    df.reset_index(inplace=True)
    
    # Rename kolom ke Bahasa Indonesia
    df.rename(columns={
        'Date': 'Tanggal',
        'Datetime': 'Tanggal',
        'Open': 'Pembukaan',
        'High': 'Tertinggi',
        'Low': 'Terendah',
        'Close': 'Penutupan',
        'Volume': 'Volume'
    }, inplace=True)
    
    return df

# Menghitung metrik penting
def hitung_metrik(df, kurs):
    """
    Menghitung statistik dasar dari data saham dalam USD dan IDR
    """
    harga_terakhir_usd = df['Penutupan'].iloc[-1]
    harga_awal_usd = df['Penutupan'].iloc[0]
    perubahan_usd = harga_terakhir_usd - harga_awal_usd
    perubahan_persen = (perubahan_usd / harga_awal_usd) * 100
    harga_tertinggi_usd = df['Tertinggi'].max()
    harga_terendah_usd = df['Terendah'].min()
    total_volume = df['Volume'].sum()
    
    # Konversi ke IDR
    harga_terakhir_idr = harga_terakhir_usd * kurs
    perubahan_idr = perubahan_usd * kurs
    harga_tertinggi_idr = harga_tertinggi_usd * kurs
    harga_terendah_idr = harga_terendah_usd * kurs
    
    return {
        'harga_terakhir_usd': harga_terakhir_usd,
        'harga_terakhir_idr': harga_terakhir_idr,
        'perubahan_usd': perubahan_usd,
        'perubahan_idr': perubahan_idr,
        'perubahan_persen': perubahan_persen,
        'harga_tertinggi_usd': harga_tertinggi_usd,
        'harga_tertinggi_idr': harga_tertinggi_idr,
        'harga_terendah_usd': harga_terendah_usd,
        'harga_terendah_idr': harga_terendah_idr,
        'total_volume': total_volume
    }

# Menambahkan indikator teknikal
def tambah_indikator(df):
    """
    Menambahkan indikator teknikal seperti SMA dan EMA
    """
    # Make sure we're working with a clean copy
    df = df.copy()
    
    # Ensure Penutupan column is a Series, not DataFrame
    harga_penutupan = df['Penutupan'].squeeze()
    
    # Simple Moving Average
    df['SMA_20'] = ta.trend.sma_indicator(harga_penutupan, window=20)
    df['SMA_50'] = ta.trend.sma_indicator(harga_penutupan, window=50)
    
    # Exponential Moving Average
    df['EMA_20'] = ta.trend.ema_indicator(harga_penutupan, window=20)
    df['EMA_50'] = ta.trend.ema_indicator(harga_penutupan, window=50)
    
    # RSI
    df['RSI'] = ta.momentum.rsi(harga_penutupan, window=14)
    
    return df

###############################################
## BAGIAN 2: Membuat Tampilan Dashboard ##
###############################################

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="Dashboard Saham Indonesia",
    page_icon="📊",
    layout="wide"
)

# Judul utama
st.title('📊 Dashboard Analisis Saham Real-Time')
st.markdown('---')

# 2A: PANEL SAMPING - PENGATURAN ############

st.sidebar.title('⚙️ Pengaturan')
st.sidebar.markdown('---')

# Input parameter dari pengguna
st.sidebar.subheader('Parameter Grafik')
kode_saham = st.sidebar.text_input('Kode Saham', 'AAPL', help='Masukkan ticker saham (contoh: AAPL, GOOGL)')

periode_waktu = st.sidebar.selectbox(
    'Periode Waktu', 
    ['1d', '1minggu', '1mo', '3mo', '1y', 'max'],
    format_func=lambda x: {
        '1d': '1 Hari',
        '1minggu': '1 Minggu', 
        '1mo': '1 Bulan',
        '3mo': '3 Bulan',
        '1y': '1 Tahun',
        'max': 'Maksimal'
    }[x]
)

tipe_grafik = st.sidebar.selectbox(
    'Tipe Grafik', 
    ['Candlestick', 'Garis', 'Area'],
    help='Pilih jenis visualisasi grafik'
)

indikator_teknikal = st.sidebar.multiselect(
    'Indikator Teknikal', 
    ['SMA 20', 'SMA 50', 'EMA 20', 'EMA 50', 'RSI'],
    help='Pilih indikator yang ingin ditampilkan'
)

# Mapping periode ke interval
pemetaan_interval = {
    '1d': '5m',
    '1minggu': '30m',
    '1mo': '1d',
    '3mo': '1d',
    '1y': '1wk',
    'max': '1wk'
}

st.sidebar.markdown('---')

# 2B: AREA KONTEN UTAMA ############

# Tombol untuk memperbarui data
if st.sidebar.button('🔄 Perbarui Data', type='primary', use_container_width=True):
    
    with st.spinner(f'Mengambil data untuk {kode_saham}...'):
        # Ambil kurs USD/IDR
        kurs_idr = ambil_kurs_usd_idr()
        
        # Ambil dan proses data
        data = ambil_data_saham(kode_saham, periode_waktu, pemetaan_interval[periode_waktu])
        
        if data.empty:
            st.error('❌ Data tidak ditemukan. Pastikan kode saham benar.')
        else:
            data = olah_data(data)
            data = tambah_indikator(data)
            
            # Hitung metrik
            metrik = hitung_metrik(data, kurs_idr)
            
            # Tampilkan kurs
            st.info(f'💱 Kurs: 1 USD = Rp {kurs_idr:,.2f}')
            
            # Tampilkan metrik utama
            st.subheader(f'📈 {kode_saham.upper()}')
            
            # Buat dua baris metrik: USD dan IDR
            st.markdown("**💵 Harga dalam USD:**")
            col_usd1, col_usd2, col_usd3, col_usd4 = st.columns(4)
            
            with col_usd1:
                # Format delta text manually with color indicator
                delta_text = f"{metrik['perubahan_usd']:.2f} ({metrik['perubahan_persen']:.2f}%)"
                st.metric(
                    label="Harga Terakhir", 
                    value=f"${metrik['harga_terakhir_usd']:.2f}",
                    delta=delta_text,
                    delta_color="normal"
                )
            
            with col_usd2:
                st.metric("Tertinggi", f"${metrik['harga_tertinggi_usd']:.2f}")
            
            with col_usd3:
                st.metric("Terendah", f"${metrik['harga_terendah_usd']:.2f}")
            
            with col_usd4:
                st.metric("Volume", f"{metrik['total_volume']:,.0f}")
            
            st.markdown("**🇮🇩 Harga dalam IDR:**")
            col_idr1, col_idr2, col_idr3, col_idr4 = st.columns(4)
            
            with col_idr1:
                # Format delta text manually with color indicator
                delta_text_idr = f"{metrik['perubahan_idr']:.0f} ({metrik['perubahan_persen']:.2f}%)"
                st.metric(
                    label="Harga Terakhir", 
                    value=f"Rp {metrik['harga_terakhir_idr']:,.0f}",
                    delta=delta_text_idr,
                    delta_color="normal"
                )
            
            with col_idr2:
                st.metric("Tertinggi", f"Rp {metrik['harga_tertinggi_idr']:,.0f}")
            
            with col_idr3:
                st.metric("Terendah", f"Rp {metrik['harga_terendah_idr']:,.0f}")
            
            with col_idr4:
                st.metric("Volume", f"{metrik['total_volume']:,.0f}")
            
            st.markdown('---')
            
            # Buat grafik harga saham
            st.subheader(f'Grafik Harga {kode_saham.upper()}')
            
            grafik = go.Figure()
            
            # Pilih tipe grafik
            if tipe_grafik == 'Candlestick':
                grafik.add_trace(go.Candlestick(
                    x=data['Tanggal'],
                    open=data['Pembukaan'],
                    high=data['Tertinggi'],
                    low=data['Terendah'],
                    close=data['Penutupan'],
                    name='Harga'
                ))
            elif tipe_grafik == 'Garis':
                grafik.add_trace(go.Scatter(
                    x=data['Tanggal'], 
                    y=data['Penutupan'],
                    mode='lines',
                    name='Harga Penutupan',
                    line=dict(color='#1f77b4', width=2)
                ))
            else:  # Area
                grafik.add_trace(go.Scatter(
                    x=data['Tanggal'], 
                    y=data['Penutupan'],
                    fill='tozeroy',
                    name='Harga Penutupan',
                    line=dict(color='#1f77b4')
                ))
            
            # Tambahkan indikator teknikal yang dipilih
            warna_indikator = {
                'SMA 20': '#ff7f0e',
                'SMA 50': '#2ca02c',
                'EMA 20': '#d62728',
                'EMA 50': '#9467bd'
            }
            
            for indikator in indikator_teknikal:
                if indikator == 'SMA 20':
                    grafik.add_trace(go.Scatter(
                        x=data['Tanggal'], 
                        y=data['SMA_20'], 
                        name='SMA 20',
                        line=dict(color=warna_indikator['SMA 20'], dash='dash')
                    ))
                elif indikator == 'SMA 50':
                    grafik.add_trace(go.Scatter(
                        x=data['Tanggal'], 
                        y=data['SMA_50'], 
                        name='SMA 50',
                        line=dict(color=warna_indikator['SMA 50'], dash='dash')
                    ))
                elif indikator == 'EMA 20':
                    grafik.add_trace(go.Scatter(
                        x=data['Tanggal'], 
                        y=data['EMA_20'], 
                        name='EMA 20',
                        line=dict(color=warna_indikator['EMA 20'], dash='dot')
                    ))
                elif indikator == 'EMA 50':
                    grafik.add_trace(go.Scatter(
                        x=data['Tanggal'], 
                        y=data['EMA_50'], 
                        name='EMA 50',
                        line=dict(color=warna_indikator['EMA 50'], dash='dot')
                    ))
            
            # Format grafik
            grafik.update_layout(
                xaxis_title='Waktu',
                yaxis_title='Harga (USD)',
                height=600,
                hovermode='x unified',
                template='plotly_white'
            )
            
            st.plotly_chart(grafik, use_container_width=True)
            
            # Grafik RSI jika dipilih
            if 'RSI' in indikator_teknikal:
                st.subheader('RSI (Relative Strength Index)')
                grafik_rsi = go.Figure()
                grafik_rsi.add_trace(go.Scatter(
                    x=data['Tanggal'], 
                    y=data['RSI'],
                    name='RSI',
                    line=dict(color='purple')
                ))
                grafik_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
                grafik_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
                grafik_rsi.update_layout(
                    xaxis_title='Waktu',
                    yaxis_title='RSI',
                    height=300,
                    template='plotly_white'
                )
                st.plotly_chart(grafik_rsi, use_container_width=True)
            
            st.markdown('---')
            
            # Tampilkan data dalam tabel
            tab1, tab2 = st.tabs(['📋 Data Historis', '📊 Indikator Teknikal'])
            
            with tab1:
                st.dataframe(
                    data[['Tanggal', 'Pembukaan', 'Tertinggi', 'Terendah', 'Penutupan', 'Volume']].tail(50),
                    use_container_width=True
                )
            
            with tab2:
                kolom_indikator = ['Tanggal', 'SMA_20', 'SMA_50', 'EMA_20', 'EMA_50', 'RSI']
                kolom_tersedia = [k for k in kolom_indikator if k in data.columns]
                st.dataframe(
                    data[kolom_tersedia].tail(50),
                    use_container_width=True
                )

else:
    # Tampilan awal sebelum data dimuat
    st.info('👈 Pilih parameter di panel samping dan klik "Perbarui Data" untuk memulai analisis')
    
    st.markdown("""
    ### 📌 Fitur Dashboard:
    - **Grafik Interaktif**: Candlestick, Garis, dan Area
    - **Indikator Teknikal**: SMA, EMA, RSI
    - **Data Real-Time**: Update data saham terkini
    - **Analisis Multi-Periode**: Dari 1 hari hingga data maksimal
    - **Dual Currency**: Tampilan harga dalam USD dan IDR
    
    ### 📖 Cara Menggunakan:
    1. Masukkan kode saham (ticker) di panel samping
    2. Pilih periode waktu dan tipe grafik
    3. Pilih indikator teknikal yang diinginkan
    4. Klik tombol "Perbarui Data"
    """)

# 2C: PANEL SAMPING - HARGA REAL-TIME ############

st.sidebar.markdown('---')
st.sidebar.subheader('💹 Harga Saham Real-Time')

# Ambil kurs untuk sidebar
kurs_sidebar = ambil_kurs_usd_idr()

daftar_saham = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']

for simbol in daftar_saham:
    try:
        data_realtime = ambil_data_saham(simbol, '1d', '5m')
        if not data_realtime.empty:
            data_realtime = olah_data(data_realtime)
            harga_sekarang = data_realtime['Penutupan'].iloc[-1]
            harga_buka = data_realtime['Pembukaan'].iloc[0]
            selisih = harga_sekarang - harga_buka
            persen_selisih = (selisih / harga_buka) * 100
            
            # Konversi ke IDR
            harga_sekarang_idr = harga_sekarang * kurs_sidebar
            
            # Format delta without dollar sign so Streamlit can detect sign
            delta_text = f"{selisih:.2f} ({persen_selisih:.2f}%)"
            
            st.sidebar.metric(
                f"{simbol}", 
                f"${harga_sekarang:.2f} / Rp {harga_sekarang_idr:,.0f}",
                delta_text,
                delta_color="normal"
            )
    except:
        st.sidebar.text(f"{simbol}: Data tidak tersedia")

# Informasi tambahan
st.sidebar.markdown('---')
st.sidebar.subheader('ℹ️ Tentang')
st.sidebar.info(
    'Dashboard ini menyediakan analisis saham real-time dengan berbagai indikator teknikal. '
    'Gunakan panel samping untuk menyesuaikan tampilan sesuai kebutuhan Anda.'
)

st.sidebar.markdown('---')
st.sidebar.caption('💡 Tips: Gunakan indikator teknikal untuk analisis yang lebih mendalam')
