import pandas as pd
import datetime

def generate_data():
    # Helper to create a week of data for an employee
    # Start date is a Monday
    def create_week(emp_id, name, start_date_str, absence_dict={}):
        start_date = pd.to_datetime(start_date_str)
        rows = []
        for i in range(7): # Mon-Sun
            current_date = start_date + datetime.timedelta(days=i)
            day_name = current_date.strftime('%A')
            
            # Default to Normal for weekdays, Hafta Sonu for weekends
            if i < 5:
                abs_type = absence_dict.get(day_name, 'Normal')
                hours = 8 if abs_type == 'Normal' else 0
            else:
                abs_type = absence_dict.get(day_name, 'Hafta Sonu')
                hours = 0
                
            rows.append({
                'Sicil No / TC': emp_id,
                'Ad Soyad': name,
                'Tarih': current_date,
                'Çalışılan Saat': hours,
                'Devamsızlık Tipi': abs_type
            })
        return rows

    data = []
    
    # Base week: 2024-05-06 (Monday)
    base_week = '2024-05-06'
    
    # TC-01: Standart tam hafta (kesintisiz)
    data.extend(create_week('1001', 'Ahmet Yılmaz', base_week))
    
    # TC-02: Tek günlük yıllık izin (hafta ortası) - Çarşamba
    data.extend(create_week('1002', 'Ayşe Demir', base_week, {'Wednesday': 'Yıllık İzin'}))
    
    # TC-03: Tek günlük rapor (hafta ortası) - Salı
    data.extend(create_week('1003', 'Mehmet Kaya', base_week, {'Tuesday': 'Rapor'}))
    
    # TC-04: Rapor Cuma gününe denk geliyor
    data.extend(create_week('1004', 'Fatma Şahin', base_week, {'Friday': 'Rapor'}))
    
    # TC-05: Rapor Pazartesi gününe denk geliyor
    data.extend(create_week('1005', 'Ali Çelik', base_week, {'Monday': 'Rapor'}))
    
    # TC-06: Aynı hafta hem rapor hem resmi tatil - Perşembe resmi tatil, Cuma rapor
    data.extend(create_week('1006', 'Veli Can', base_week, {'Thursday': 'Resmi Tatil', 'Friday': 'Rapor'}))
    
    # TC-07: Aynı haftada yıllık izin + resmi tatil birlikte - Salı yıllık izin, Perşembe resmi tatil
    data.extend(create_week('1007', 'Zeynep Yıldız', base_week, {'Tuesday': 'Yıllık İzin', 'Thursday': 'Resmi Tatil'}))
    
    # TC-08: Rapor tüm hafta boyunca (5 iş günü)
    all_week_report = {day: 'Rapor' for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']}
    data.extend(create_week('1008', 'Mustafa Koç', base_week, all_week_report))
    
    # TC-09: Ay sonu haftasının bölünmesi (31'i Cuma)
    # 2024-05-27 is Monday, 2024-05-31 is Friday
    data.extend(create_week('1009', 'Elif Öztürk', '2024-05-27'))
    
    df = pd.DataFrame(data)
    
    # Export to Excel
    output_path = 'ornek_puantaj.xlsx'
    df.to_excel(output_path, index=False)
    print(f"{output_path} başarıyla oluşturuldu!")

if __name__ == '__main__':
    generate_data()
