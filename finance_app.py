import streamlit as st
import psycopg2
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import locale
import re

# Set locale untuk format angka Indonesia
try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Indonesian_Indonesia.1252')
    except:
        pass

# Database configuration - DETAIL SUPABASE ANDA
# Database configuration menggunakan secrets
DB_CONFIG = {
    "host": st.secrets["db"]["DB_HOST"],
    "port": st.secrets["db"]["DB_PORT"],
    "database": st.secrets["db"]["DB_NAME"],
    "user": st.secrets["db"]["DB_USER"],
    "password": st.secrets["db"]["DB_PASSWORD"]
}

# Fungsi untuk format angka dengan titik sebagai pemisah ribuan
def format_angka(angka):
    try:
        return f"Rp {angka:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"Rp 0"

# Fungsi untuk format input dengan koma - DIPERBAIKI
def format_input_angka(angka_str):
    """Format input angka dengan koma sebagai pemisah ribuan"""
    if not angka_str:
        return ""
    
    # Hapus semua karakter non-digit
    angka_clean = re.sub(r'[^\d]', '', str(angka_str))
    
    if not angka_clean:
        return ""
    
    # Konversi ke integer
    try:
        angka_int = int(angka_clean)
    except:
        return angka_str
    
    # Format dengan koma sebagai pemisah ribuan
    formatted = f"{angka_int:,}"
    return formatted

# Fungsi untuk parse input angka dengan format
def parse_angka_input(angka_str):
    """Parse input angka yang mungkin mengandung koma sebagai pemisah"""
    if not angka_str:
        return 0
    
    # Hapus semua koma dan karakter non-digit
    angka_clean = re.sub(r'[^\d]', '', str(angka_str))
    
    try:
        return int(angka_clean) if angka_clean else 0
    except:
        return 0

# Custom input dengan auto-format - DIPERBAIKI
def number_input_auto_format(label, value="", key=None, placeholder=""):
    """Input number dengan auto-format koma"""
    if key not in st.session_state:
        st.session_state[key] = value
    
    # Input text
    input_val = st.text_input(label, value=st.session_state[key],
                              placeholder=placeholder, key=f"{key}_input")
    
    # Auto-format saat input berubah
    if input_val != st.session_state[key]:
        # Format angka
        formatted = format_input_angka(input_val)
        st.session_state[key] = formatted
        
        # Trigger rerun untuk update tampilan
        st.rerun()
    
    return st.session_state[key]

# Initialize connection - menggunakan singleton pattern
def get_connection():
    try:
        conn = psycopg2.connect(st.secrets["db"]["DATABASE_URL"])
        return conn
    except Exception as e:
        st.error(f"❌ Error connecting to database: {e}")
        return None

# Create tables if they don't exist
def create_tables():
    """Create tables if they don't exist"""
    conn = get_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pemasukan (
                id SERIAL PRIMARY KEY,
                jenis VARCHAR(50) NOT NULL,
                keterangan TEXT,
                jumlah INTEGER NOT NULL,
                tanggal DATE DEFAULT CURRENT_DATE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pengeluaran (
                id SERIAL PRIMARY KEY,
                jenis VARCHAR(50) NOT NULL,
                keterangan TEXT,
                jumlah INTEGER NOT NULL,
                tanggal DATE DEFAULT CURRENT_DATE
            )
        """)
        
        conn.commit()
        cur.close()
    except Exception as e:
        st.error(f"Error creating tables: {e}")
    finally:
        conn.close()

def execute_query(query, params=None, fetch=False):
    """Execute database query with proper connection handling"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        
        if fetch:
            result = cur.fetchall()
        else:
            conn.commit()
            result = None
        
        cur.close()
        return result
        
    except Exception as e:
        st.error(f"❌ Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def show_dashboard():
    st.header("📊 Dashboard Keuangan")
    
    try:
        # Get current month and year
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        # Calculate total pemasukan this month
        pemasukan_result = execute_query(
            "SELECT COALESCE(SUM(jumlah), 0) FROM pemasukan WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s",
            (current_month, current_year),
            fetch=True
        )
        total_pemasukan = pemasukan_result[0][0] if pemasukan_result else 0
        
        # Calculate total pengeluaran this month
        pengeluaran_result = execute_query(
            "SELECT COALESCE(SUM(jumlah), 0) FROM pengeluaran WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s",
            (current_month, current_year),
            fetch=True
        )
        total_pengeluaran = pengeluaran_result[0][0] if pengeluaran_result else 0
        
        # Calculate saldo
        saldo = total_pemasukan - total_pengeluaran
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Pemasukan", format_angka(total_pemasukan))
        col2.metric("💸 Total Pengeluaran", format_angka(total_pengeluaran))
        col3.metric("✅ Saldo Bulan Ini", format_angka(saldo),
                    f"{'Surplus' if saldo >= 0 else 'Defisit'}")
        
        # Get data for charts
        pemasukan_data = execute_query(
            "SELECT jenis, SUM(jumlah) FROM pemasukan WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s GROUP BY jenis",
            (current_month, current_year),
            fetch=True
        ) or []
        
        pengeluaran_data = execute_query(
            "SELECT jenis, SUM(jumlah) FROM pengeluaran WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s GROUP BY jenis",
            (current_month, current_year),
            fetch=True
        ) or []
        
        # Create charts
        col1, col2 = st.columns(2)
        
        if pemasukan_data:
            df_pemasukan = pd.DataFrame(pemasukan_data, columns=['Jenis', 'Jumlah'])
            fig_pemasukan = px.pie(df_pemasukan, values='Jumlah', names='Jenis',
                                   title='📈 Komposisi Pemasukan', hole=0.4)
            col1.plotly_chart(fig_pemasukan, use_container_width=True)
        else:
            col1.info("📝 Belum ada data pemasukan bulan ini")
        
        if pengeluaran_data:
            df_pengeluaran = pd.DataFrame(pengeluaran_data, columns=['Jenis', 'Jumlah'])
            fig_pengeluaran = px.pie(df_pengeluaran, values='Jumlah', names='Jenis',
                                     title='📉 Komposisi Pengeluaran', hole=0.4)
            col2.plotly_chart(fig_pengeluaran, use_container_width=True)
        else:
            col2.info("📝 Belum ada data pengeluaran bulan ini")
        
    except Exception as e:
        st.error(f"Error loading dashboard data: {e}")

def input_pemasukan():
    st.header("💵 Input Pemasukan")
    
    st.info("💡 Ketik angka dan akan otomatis diformat dengan koma (contoh: 1,000,000)")
    
    with st.form("pemasukan_form"):
        jenis = st.selectbox(
            "Jenis Pemasukan",
            ["Pemasukan Truck", "Pemasukan Gaji", "Pemasukan Lainnya"]
        )
        
        # Input jumlah dengan auto-format
        jumlah_input = number_input_auto_format(
            "Jumlah Pemasukan",
            value="",
            key="pemasukan_jumlah",
            placeholder="Ketik angka (contoh: 1000000)"
        )
        
        jumlah = parse_angka_input(jumlah_input)
        
        if jumlah_input:
            st.caption(f"✅ Jumlah yang akan disimpan: {format_angka(jumlah)}")
        else:
            st.caption("💡 Contoh: ketik '1000000' akan menjadi '1,000,000'")
        
        keterangan = st.text_input("Keterangan", placeholder="Deskripsi pemasukan")
        
        tanggal = st.date_input("Tanggal Pemasukan", date.today())
        
        submitted = st.form_submit_button("💾 Simpan Pemasukan")
        
        if submitted:
            if jumlah <= 0:
                st.error("❌ Jumlah pemasukan harus lebih dari 0")
            elif not keterangan.strip():
                st.error("❌ Keterangan harus diisi")
            else:
                try:
                    execute_query(
                        "INSERT INTO pemasukan (jenis, keterangan, jumlah, tanggal) VALUES (%s, %s, %s, %s)",
                        (jenis, keterangan, jumlah, tanggal)
                    )
                    st.success("✅ Pemasukan berhasil dicatat!")
                    # Reset input
                    st.session_state.pemasukan_jumlah = ""
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error menyimpan pemasukan: {e}")

def input_pengeluaran():
    st.header("💸 Input Pengeluaran")
    
    st.info("💡 Ketik angka dan akan otomatis diformat dengan koma (contoh: 500,000)")
    
    with st.form("pengeluaran_form"):
        jenis = st.selectbox(
            "Jenis Pengeluaran",
            ["Perbaikan Truck", "Kebutuhan Rumah", "Pengeluaran Lainnya"]
        )
        
        # Input jumlah dengan auto-format
        jumlah_input = number_input_auto_format(
            "Jumlah Pengeluaran",
            value="",
            key="pengeluaran_jumlah",
            placeholder="Ketik angka (contoh: 500000)"
        )
        
        jumlah = parse_angka_input(jumlah_input)
        
        if jumlah_input:
            st.caption(f"✅ Jumlah yang akan disimpan: {format_angka(jumlah)}")
        else:
            st.caption("💡 Contoh: ketik '500000' akan menjadi '500,000'")
        
        keterangan = st.text_input("Keterangan", placeholder="Deskripsi pengeluaran")
        
        tanggal = st.date_input("Tanggal Pengeluaran", date.today())
        
        submitted = st.form_submit_button("💾 Simpan Pengeluaran")
        
        if submitted:
            if jumlah <= 0:
                st.error("❌ Jumlah pengeluaran harus lebih dari 0")
            elif not keterangan.strip():
                st.error("❌ Keterangan harus diisi")
            else:
                try:
                    execute_query(
                        "INSERT INTO pengeluaran (jenis, keterangan, jumlah, tanggal) VALUES (%s, %s, %s, %s)",
                        (jenis, keterangan, jumlah, tanggal)
                    )
                    st.success("✅ Pengeluaran berhasil dicatat!")
                    # Reset input
                    st.session_state.pengeluaran_jumlah = ""
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error menyimpan pengeluaran: {e}")

def kalkulator_truck():
    st.header("🚛 Kalkulator Truck")
    
    st.info("💡 Ketik angka dan akan otomatis diformat dengan koma. Hasil perhitungan akan ditampilkan secara otomatis setelah input diisi.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Input Data")
        
        # Input dengan auto-format
        berangkat_input = number_input_auto_format(
            "Jumlah Berangkat",
            value="",
            key="berangkat",
            placeholder="Ketik angka (contoh: 500000)"
        )
        berangkat = parse_angka_input(berangkat_input)
        if berangkat_input:
            st.caption(f"✅ Berangkat: {format_angka(berangkat)}")
        else:
            st.caption("💡 Contoh: ketik '500000' akan menjadi '500,000'")
        
        pulang_input = number_input_auto_format(
            "Jumlah Pulang",
            value="",
            key="pulang",
            placeholder="Ketik angka (contoh: 300000)"
        )
        pulang = parse_angka_input(pulang_input)
        if pulang_input:
            st.caption(f"✅ Pulang: {format_angka(pulang)}")
        else:
            st.caption("💡 Contoh: ketik '300000' akan menjadi '300,000'")
        
        sangu_input = number_input_auto_format(
            "Sangu Supir",
            value="",
            key="sangu",
            placeholder="Ketik angka (contoh: 100000)"
        )
        sangu_supir = parse_angka_input(sangu_input)
        if sangu_input:
            st.caption(f"✅ Sangu Supir: {format_angka(sangu_supir)}")
        else:
            st.caption("💡 Contoh: ketik '100000' akan menjadi '100,000'")
        
        # Input keterangan custom
        keterangan_custom = st.text_input("Keterangan Pendapatan Truck",
                                          placeholder="Masukkan keterangan untuk pendapatan truck")
    
    with col2:
        st.subheader("Perhitungan")
        
        if berangkat > 0 and pulang > 0 and sangu_supir > 0:
            total = berangkat + pulang - sangu_supir
            st.info(f"""
            **Hasil Perhitungan:**
            - Berangkat: {format_angka(berangkat)}
            - Pulang: {format_angka(pulang)}
            - Sangu Supir: {format_angka(sangu_supir)}
            - **Total: {format_angka(total)}**
            """)
            
            # Tampilkan preview keterangan
            if keterangan_custom:
                st.write(f"**Keterangan:** {keterangan_custom}")
            
            if st.button("💰 Masukkan ke Pendapatan Truck"):
                if not keterangan_custom.strip():
                    st.error("❌ Keterangan harus diisi")
                else:
                    try:
                        execute_query(
                            "INSERT INTO pemasukan (jenis, keterangan, jumlah) VALUES (%s, %s, %s)",
                            ("Pemasukan Truck",
                             keterangan_custom,
                             total)
                        )
                        st.success("✅ Pendapatan truck berhasil dicatat!")
                        # Clear inputs
                        st.session_state.berangkat = ""
                        st.session_state.pulang = ""
                        st.session_state.sangu = ""
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error menyimpan pendapatan truck: {e}")
        else:
            st.warning("⚠️ Silakan isi semua field jumlah untuk melihat perhitungan.")

def laporan_keuangan():
    st.header("📋 Laporan Keuangan Bulanan")
    
    # Date selection
    col1, col2 = st.columns(2)
    with col1:
        tahun = st.selectbox("Tahun", range(2020, datetime.now().year + 1),
                             index=datetime.now().year - 2020, key="laporan_tahun")
    with col2:
        bulan = st.selectbox("Bulan", range(1, 13),
                             format_func=lambda x: datetime(2000, x, 1).strftime('%B'),
                             index=datetime.now().month - 1, key="laporan_bulan")
    
    try:
        # Get pemasukan data
        pemasukan_data = execute_query(
            "SELECT id, jenis, keterangan, jumlah, tanggal FROM pemasukan WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s ORDER BY tanggal DESC",
            (bulan, tahun),
            fetch=True
        ) or []
        
        # Get pengeluaran data
        pengeluaran_data = execute_query(
            "SELECT id, jenis, keterangan, jumlah, tanggal FROM pengeluaran WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s ORDER BY tanggal DESC",
            (bulan, tahun),
            fetch=True
        ) or []
        
        # Calculate totals
        total_pemasukan = sum([p[3] for p in pemasukan_data]) if pemasukan_data else 0
        total_pengeluaran = sum([p[3] for p in pengeluaran_data]) if pengeluaran_data else 0
        saldo = total_pemasukan - total_pengeluaran
        
        # Display totals
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total Pemasukan", format_angka(total_pemasukan))
        col2.metric("💸 Total Pengeluaran", format_angka(total_pengeluaran))
        col3.metric("✅ Saldo", format_angka(saldo),
                    f"{'Surplus' if saldo >= 0 else 'Defisit'}")
        
        # Display pemasukan table
        st.subheader("📈 Daftar Pemasukan")
        if pemasukan_data:
            df_pemasukan = pd.DataFrame(pemasukan_data, columns=['ID', 'Jenis', 'Keterangan', 'Jumlah', 'Tanggal'])
            df_pemasukan['Jumlah'] = df_pemasukan['Jumlah'].apply(lambda x: format_angka(x))
            st.dataframe(df_pemasukan, use_container_width=True, hide_index=True)
            
            # Export option
            csv_pemasukan = df_pemasukan.to_csv(index=False)
            st.download_button("📥 Download Pemasukan (CSV)", csv_pemasukan,
                               f"pemasukan_{bulan}_{tahun}.csv", "text/csv")
        else:
            st.info("📝 Tidak ada data pemasukan untuk periode ini")
        
        # Display pengeluaran table
        st.subheader("📉 Daftar Pengeluaran")
        if pengeluaran_data:
            df_pengeluaran = pd.DataFrame(pengeluaran_data, columns=['ID', 'Jenis', 'Keterangan', 'Jumlah', 'Tanggal'])
            df_pengeluaran['Jumlah'] = df_pengeluaran['Jumlah'].apply(lambda x: format_angka(x))
            st.dataframe(df_pengeluaran, use_container_width=True, hide_index=True)
            
            # Export option
            csv_pengeluaran = df_pengeluaran.to_csv(index=False)
            st.download_button("📥 Download Pengeluaran (CSV)", csv_pengeluaran,
                               f"pengeluaran_{bulan}_{tahun}.csv", "text/csv")
        else:
            st.info("📝 Tidak ada data pengeluaran untuk periode ini")
        
    except Exception as e:
        st.error(f"❌ Error loading report data: {e}")

def laporan_tahunan():
    st.header("📊 Laporan Tahunan")
    
    # Tahun selection
    tahun = st.selectbox("Pilih Tahun", range(2020, datetime.now().year + 1),
                         index=datetime.now().year - 2020, key="tahunan_tahun")
    
    try:
        # Get pemasukan data per bulan
        pemasukan_per_bulan = execute_query("""
            SELECT EXTRACT(MONTH FROM tanggal) as bulan,
                   COALESCE(SUM(jumlah), 0) as total
            FROM pemasukan
            WHERE EXTRACT(YEAR FROM tanggal) = %s
            GROUP BY EXTRACT(MONTH FROM tanggal)
            ORDER BY bulan
        """, (tahun,), fetch=True) or []
        
        # Get pengeluaran data per bulan
        pengeluaran_per_bulan = execute_query("""
            SELECT EXTRACT(MONTH FROM tanggal) as bulan,
                   COALESCE(SUM(jumlah), 0) as total
            FROM pengeluaran
            WHERE EXTRACT(YEAR FROM tanggal) = %s
            GROUP BY EXTRACT(MONTH FROM tanggal)
            ORDER BY bulan
        """, (tahun,), fetch=True) or []
        
        # Create data for chart
        bulan_list = list(range(1, 13))
        nama_bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                      'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        
        # Prepare data for DataFrame
        data = []
        for bulan in bulan_list:
            pemasukan = next((p[1] for p in pemasukan_per_bulan if p[0] == bulan), 0)
            pengeluaran = next((p[1] for p in pengeluaran_per_bulan if p[0] == bulan), 0)
            data.append({
                'Bulan': nama_bulan[bulan-1],
                'Pemasukan': pemasukan,
                'Pengeluaran': pengeluaran
            })
        
        df = pd.DataFrame(data)
        
        # Melt data untuk chart
        df_melted = pd.melt(df, id_vars=['Bulan'], value_vars=['Pemasukan', 'Pengeluaran'],
                            var_name='Jenis', value_name='Jumlah')
        
        # Create vertical bar chart (grafik batang vertikal)
        fig = px.bar(df_melted,
                     x='Bulan',
                     y='Jumlah',
                     color='Jenis',
                     title=f'Laporan Keuangan Tahunan {tahun}',
                     labels={'Jumlah': 'Jumlah (Rp)', 'Bulan': ''},
                     color_discrete_map={'Pemasukan': '#00CC96', 'Pengeluaran': '#EF553B'},
                     barmode='group',
                     hover_data={'Jumlah': ':,', 'Jenis': True})
        
        # Format tooltip untuk menampilkan angka dengan format
        fig.update_traces(hovertemplate='<b>%{x}</b><br>%{y:,.0f} <extra></extra>')
        
        # Update layout untuk grafik vertikal
        fig.update_layout(
            xaxis={'categoryorder': 'array', 'categoryarray': nama_bulan},
            yaxis_tickformat = ',.0f',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display detailed table
        st.subheader("📋 Rincian Bulanan")
        
        # Calculate totals
        df['Saldo'] = df['Pemasukan'] - df['Pengeluaran']
        
        # Format numbers for display
        df_display = df.copy()
        df_display['Pemasukan'] = df_display['Pemasukan'].apply(format_angka)
        df_display['Pengeluaran'] = df_display['Pengeluaran'].apply(format_angka)
        df_display['Saldo'] = df_display['Saldo'].apply(format_angka)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Add expanders for monthly details
        for idx, row in df.iterrows():
            bulan_num = idx + 1
            with st.expander(f"📅 Detail {nama_bulan[idx]} {tahun} - Saldo: {format_angka(row['Saldo'])}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("💰 Pemasukan")
                    pemasukan_detail = execute_query(
                        "SELECT jenis, keterangan, jumlah, tanggal FROM pemasukan WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s ORDER BY tanggal DESC",
                        (bulan_num, tahun),
                        fetch=True
                    ) or []
                    
                    if pemasukan_detail:
                        total_bulan = sum([p[2] for p in pemasukan_detail])
                        st.metric("Total Pemasukan", format_angka(total_bulan))
                        
                        for p in pemasukan_detail:
                            st.write(f"**{p[0]}**")
                            st.write(f"{format_angka(p[2])} - {p[1]}")
                            st.caption(f"Tanggal: {p[3].strftime('%d %b %Y')}")
                            st.divider()
                    else:
                        st.info("Tidak ada pemasukan")
                
                with col2:
                    st.subheader("💸 Pengeluaran")
                    pengeluaran_detail = execute_query(
                        "SELECT jenis, keterangan, jumlah, tanggal FROM pengeluaran WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s ORDER BY tanggal DESC",
                        (bulan_num, tahun),
                        fetch=True
                    ) or []
                    
                    if pengeluaran_detail:
                        total_bulan = sum([p[2] for p in pengeluaran_detail])
                        st.metric("Total Pengeluaran", format_angka(total_bulan))
                        
                        for p in pengeluaran_detail:
                            st.write(f"**{p[0]}**")
                            st.write(f"{format_angka(p[2])} - {p[1]}")
                            st.caption(f"Tanggal: {p[3].strftime('%d %b %Y')}")
                            st.divider()
                    else:
                        st.info("Tidak ada pengeluaran")
        
    except Exception as e:
        st.error(f"❌ Error loading annual report: {e}")

def hapus_data():
    st.header("🗑️ Hapus Data")
    
    # Pilih bulan dan tahun
    col1, col2 = st.columns(2)
    with col1:
        tahun = st.selectbox("Tahun", range(2020, datetime.now().year + 1),
                             index=datetime.now().year - 2020, key="hapus_tahun")
    with col2:
        bulan = st.selectbox("Bulan", range(1, 13),
                             format_func=lambda x: datetime(2000, x, 1).strftime('%B'),
                             index=datetime.now().month - 1, key="hapus_bulan")
    
    # Pilih jenis data
    jenis_data = st.radio("Jenis Data", ["Pemasukan", "Pengeluaran"])
    
    try:
        if jenis_data == "Pemasukan":
            # Get pemasukan data
            data = execute_query(
                "SELECT id, jenis, keterangan, jumlah, tanggal FROM pemasukan WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s ORDER BY tanggal DESC",
                (bulan, tahun),
                fetch=True
            ) or []
            table_name = "pemasukan"
        else:
            # Get pengeluaran data
            data = execute_query(
                "SELECT id, jenis, keterangan, jumlah, tanggal FROM pengeluaran WHERE EXTRACT(MONTH FROM tanggal) = %s AND EXTRACT(YEAR FROM tanggal) = %s ORDER BY tanggal DESC",
                (bulan, tahun),
                fetch=True
            ) or []
            table_name = "pengeluaran"
        
        if data:
            df = pd.DataFrame(data, columns=['ID', 'Jenis', 'Keterangan', 'Jumlah', 'Tanggal'])
            df['Jumlah'] = df['Jumlah'].apply(lambda x: format_angka(x))
            
            if not df.empty:
                st.subheader(f"Daftar {jenis_data}")
                
                # Add selection column
                df['Pilih'] = False
                edited_df = st.data_editor(df, use_container_width=True, hide_index=True,
                                           column_config={
                                               "Pilih": st.column_config.CheckboxColumn(required=True),
                                               "ID": None,
                                               "Jenis": None,
                                               "Keterangan": None,
                                               "Jumlah": None,
                                               "Tanggal": None
                                           })
                
                # Get selected rows
                selected_rows = edited_df[edited_df['Pilih']]
                
                if not selected_rows.empty:
                    st.warning(f"⚠️ Anda akan menghapus {len(selected_rows)} data {jenis_data.lower()}")
                    
                    st.subheader("Detail Data yang Akan Dihapus (Keterangan dan Nominal)")
                    display_df = selected_rows[['Keterangan', 'Jumlah', 'Jenis', 'Tanggal']]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    if st.button("🗑️ Hapus Data Terpilih", type="primary"):
                        try:
                            # Delete selected records
                            for idx, row in selected_rows.iterrows():
                                # Get the original ID from the data (not from the displayed DF)
                                original_id = data[idx][0]
                                execute_query(f"DELETE FROM {table_name} WHERE id = %s", (original_id,))
                            
                            st.success("✅ Data berhasil dihapus!")
                            st.rerun() # Refresh the page
                        except Exception as e:
                            st.error(f"❌ Error menghapus data: {e}")
            else:
                st.info(f"Tidak ada data {jenis_data.lower()} untuk periode ini")
        else:
            st.info(f"Tidak ada data {jenis_data.lower()} untuk periode ini")
        
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")

def main():
    st.set_page_config(
        page_title="Sistem Manajemen Keuangan",
        page_icon="💰",
        layout="wide"
    )
    
    st.title("💰 Sistem Manajemen Keuangan")
    st.sidebar.header("Menu Navigasi")
    
    # Initialize database tables
    create_tables()
    
    # Sidebar navigation
    menu = st.sidebar.selectbox(
        "Menu Utama",
        ["Dashboard", "Pemasukan", "Pengeluaran", "Kalkulator Truck",
         "Laporan Keuangan", "Laporan Tahunan", "Hapus Data"]
    )
    
    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Pemasukan":
        input_pemasukan()
    elif menu == "Pengeluaran":
        input_pengeluaran()
    elif menu == "Kalkulator Truck":
        kalkulator_truck()
    elif menu == "Laporan Keuangan":
        laporan_keuangan()
    elif menu == "Laporan Tahunan":
        laporan_tahunan()
    elif menu == "Hapus Data":
        hapus_data()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("🔗 Connected to: kknqpdhkcopfhjqiklne.supabase.co")

if __name__ == "__main__":
    main()
