import pandas as pd
import datetime
import calendar

def generate_data():
    # Helper to create a whole month of data for an employee
    def create_month(emp_id, name, year, month, absence_dict={}):
        rows = []
        num_days = calendar.monthrange(year, month)[1]
        
        for i in range(1, num_days + 1):
            current_date = datetime.date(year, month, i)
            day_name = current_date.strftime('%A')
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Default to Normal for weekdays, Hafta Sonu for weekends
            if current_date.weekday() < 5:
                abs_type = absence_dict.get(date_str, 'Normal')
                hours = 8 if abs_type == 'Normal' else 0
            else:
                abs_type = absence_dict.get(date_str, 'Hafta Sonu')
                hours = 0
                
            rows.append({
                'Sicil No / TC': emp_id,
                'Ad Soyad': name,
                'Tarih': pd.to_datetime(current_date),
                'Çalışılan Saat': hours,
                'Devamsızlık Tipi': abs_type
            })
        return rows

    data = []
    
    year, month = 2024, 6 # Haziran 2024 (Kurban Bayramı tatili falan da eklenebilir)
    
    # TC-01: Tam ay eksiksiz çalışan
    data.extend(create_month('2001', 'Canan Yılmaz', year, month))
    
    # TC-02: 1 hafta Ücretsiz İzin (3-7 Haziran)
    ucretsiz_izin = {f'2024-06-0{i}': 'Ücretsiz İzin' for i in range(3, 8)}
    data.extend(create_month('2002', 'Kemal Sunal', year, month, ucretsiz_izin))
    
    # TC-03: Haziran 20-21 Yıllık İzin
    yillik_izin = {'2024-06-20': 'Yıllık İzin', '2024-06-21': 'Yıllık İzin'}
    data.extend(create_month('2003', 'Ayşen Gruda', year, month, yillik_izin))
    
    # TC-04: Kurban Bayramı (17-19 Haziran resmi tatil varsayalım) + 20-21 Haziran Rapor
    karisik_izin = {
        '2024-06-17': 'Resmi Tatil',
        '2024-06-18': 'Resmi Tatil',
        '2024-06-19': 'Resmi Tatil',
        '2024-06-20': 'Rapor',
        '2024-06-21': 'Rapor'
    }
    data.extend(create_month('2004', 'Şener Şen', year, month, karisik_izin))
    
    # TC-05: Hafta sonuna denk gelen resmi tatil veya özel durum (Maaşa/Puantaja etkisi test edilir)
    haftasonu_izin = {'2024-06-15': 'Resmi Tatil', '2024-06-16': 'Resmi Tatil'}
    data.extend(create_month('2005', 'Adile Naşit', year, month, haftasonu_izin))
    
    df = pd.DataFrame(data)
    
    # Export to Excel
    output_path = 'ornek_puantaj_2.xlsx'
    df.to_excel(output_path, index=False)
    print(f"{output_path} başarıyla oluşturuldu!")

if __name__ == '__main__':
    generate_data()
