from flask import Flask, request, jsonify, send_file, session 
from flask_cors import CORS 
from werkzeug.exceptions import RequestEntityTooLarge 
import io
import os
import datetime
import base64
from PIL import Image
import numpy as np

# استيراد دالة التحليل
try:
    from ai_forensics import analyze_full_forensics
except ImportError:
    print("FATAL ERROR: Could not import ai_forensics.py. Analysis will fail.")
    def analyze_full_forensics(image_stream):
        return {'abshr_verdict': 'ERROR', 'final_score': 0, 'ai_score': 0, 'prnu_score': 0, 'ela_score': 0, 'ai_verdict': 'فشل حاد في تحميل دالة التحليل.', 'prnu_verdict': '', 'ela_verdict': '', 'metadata': {}, 'prnu_img_base64': None, 'ela_img_base64': None, 'gradcam_img_base64': None, 'original_img_base64': None}

def clean_for_json(data):
    """
    تحويل أنواع بيانات NumPy إلى أنواع قياسية في Python يمكن لـ JSON التعامل معها.
    """
    if isinstance(data, dict):
        return {k: clean_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_for_json(item) for item in data]
    elif isinstance(data, (np.float32, np.float64)):
        # 🌟🌟🌟 الإصلاح 2: تحويل Float32 إلى Float قياسي 🌟🌟🌟
        return float(data)
    else:
        return data
# =========================================================
# 1. إعدادات وتكوين التطبيق
# =========================================================

app = Flask(__name__) 
CORS(app) 
# يجب أن يكون المفتاح السري موجوداً لتمكين الجلسات (session)
app.secret_key = os.environ.get("SECRET_KEY", 'a_secure_secret_key_for_sidq') 
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 # 5 ميجابايت

# =========================================================
# 2. إعدادات التقرير (ReportLab)
# =========================================================

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.utils import ImageReader
    from reportlab.lib import colors
    
    # ⚠️ **هام:** يجب أن يكون ملف الخط 'Tajawal-Bold.ttf' موجوداً
    pdfmetrics.registerFont(TTFont('Tajawal', 'Tajawal-Bold.ttf'))
    ARABIC_FONT = 'Tajawal'
except Exception as e:
    print(f"WARNING: فشل تحميل خط Tajawal أو ReportLab: {e}. سيتم استخدام الخط الافتراضي.")
    ARABIC_FONT = 'Helvetica'


# =========================================================
# 3. نقطة نهاية تحليل الأمن (الربط مع أبشر) - مُحدثة
# =========================================================

@app.route('/api/abshr/security-forensics', methods=['POST'])
def abshr_security_forensics():
    try:
        if 'image' not in request.files:
            return jsonify({'status': 'error', 'message': 'لم يتم العثور على ملف الصورة.'}), 400

        file = request.files['image']
        image_stream = io.BytesIO(file.read())
        
        # 1. تنفيذ التحليل الجنائي الكامل
        full_analysis_data = analyze_full_forensics(image_stream)
        
        # 2. حفظ نتائج التحليل الكاملة في جلسة المستخدم (لتوليد التقرير لاحقاً)
        # يجب تخزين البيانات في الجلسة لاستخدامها في /api/report
        session['last_analysis_results'] = full_analysis_data 
        session['analysis_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 3. إرجاع النتيجة الأساسية لـ واجهة أبشر
        response_to_abshr = {
            'status': 'success',
            # درجة الثقة النهائية (الختم الأمني)
            'confidence_score': full_analysis_data['final_score'], 
            # القرار الأمني (CLEAN, CAUTION, FORGED)
            'abshr_verdict': full_analysis_data['abshr_verdict'], 
            # URL التقرير الذي سيستدعيه الزر في الواجهة
            'report_url': '/api/report' 
        }

        return jsonify(response_to_abshr)

    except RequestEntityTooLarge:
        return jsonify({'status': 'error', 'message': 'حجم الملف يتجاوز الحد الأقصى (5MB).'}), 413
    except Exception as e:
        print(f"Error during forensics analysis: {e}")
        return jsonify({'status': 'error', 'message': f'فشل في عملية التحليل: {str(e)}'}), 500


# =========================================================
# 4. نقطة نهاية توليد تقرير PDF (المطلوبة!) - تمت الإضافة
# =========================================================

@app.route('/api/report', methods=['GET'])
def generate_report():
    
    # 1. التحقق من وجود نتائج تحليل سابقة في الجلسة
    analysis_data = session.get('last_analysis_results')
    timestamp = session.get('analysis_timestamp', 'غير متوفر')
    
    if not analysis_data:
        return jsonify({'status': 'error', 'message': 'لا توجد نتائج تحليل سابقة لإصدار تقرير.'}), 404

    # 2. تهيئة ملف PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # إعداد الخط الأساسي
    font_size = 12
    p.setFont(ARABIC_FONT, font_size)
    line_height = font_size * 1.5
    margin = 50
    x, y = width - margin, height - margin

    # 3. رأس التقرير والختم
    p.setFont(ARABIC_FONT, 20)
    p.drawRightString(x, y, "تقرير الأدلة الجنائية لخدمة صِدق (Sidq Report)")
    y -= line_height * 2
    
    p.setFont(ARABIC_FONT, 10)
    p.drawRightString(x, y, f"تاريخ ووقت التحليل: {timestamp}")
    y -= line_height

    # 4. قسم القرار الأمني (الختم)
    p.setFillColor(colors.white)
    
    if analysis_data['abshr_verdict'] == 'CLEAN':
        box_color = colors.green
        verdict_text = "✅ أصالة مُؤكَّدة (CLEAN)"
    elif analysis_data['abshr_verdict'] == 'CAUTION':
        box_color = colors.orange
        verdict_text = "⚠️ احتمالية تلاعب (CAUTION)"
    else:
        box_color = colors.red
        verdict_text = "❌ تزوير مُؤكَّد (FORGED)"
        
    p.setFillColor(box_color)
    p.rect(margin, y - 50, width - 2 * margin, 60, fill=1) # رسم مستطيل خلفي
    
    p.setFillColor(colors.white)
    p.setFont(ARABIC_FONT, 18)
    p.drawCentredString(width / 2, y - 30, verdict_text)
    y -= line_height * 4

    # 5. جدول المعلومات الأساسية
    p.setFillColor(colors.black)
    p.setFont(ARABIC_FONT, font_size)
    p.drawRightString(x, y, "أ. البيانات الأساسية للوثيقة")
    y -= line_height
    
    # دالة بسيطة لرسم سطر المعلومات
    def draw_info_line(key, value):
        nonlocal y
        p.setFont(ARABIC_FONT, font_size)
        p.drawRightString(x, y, key)
        p.drawString(margin + 150, y, str(value))
        y -= line_height
    
    draw_info_line("الدرجة النهائية:", f"{analysis_data['final_score']:.2f}%")
    draw_info_line("صانع الكاميرا:", analysis_data['metadata']['make'])
    draw_info_line("طراز الكاميرا:", analysis_data['metadata']['model'])
    draw_info_line("تاريخ الالتقاط:", analysis_data['metadata']['datetime'])
    draw_info_line("الأبعاد (بكسل):", analysis_data['metadata']['size'])
    draw_info_line("صيغة الملف:", analysis_data['metadata']['format'])
    y -= line_height

    # 6. قسم نتائج التحليل التفصيلية (التحليل الجنائي)
    p.drawRightString(x, y, "ب. نتائج التحليل الجنائي")
    y -= line_height
    
    # دالة لرسم قسم التحليل
    def draw_analysis_section(title, score, verdict, base64_img):
        nonlocal y
        p.setFillColor(colors.blue)
        p.setFont(ARABIC_FONT, font_size)
        p.drawRightString(x, y, title)
        y -= line_height
        
        p.setFillColor(colors.black)
        draw_info_line("الدرجة:", f"{score:.2f}%")
        draw_info_line("الخلاصة:", verdict)
        y -= line_height
        
        # عرض صورة الدليل الجنائي
        if base64_img:
            try:
                img_data = base64.b64decode(base64_img)
                img_stream = io.BytesIO(img_data)
                img = ImageReader(img_stream)
                # رسم الصورة (300 بكسل عرض)
                img_w, img_h = 300, 300 * (img.getSize()[1] / img.getSize()[0])
                
                # التحقق من تجاوز حدود الصفحة
                if y - img_h < margin:
                    p.showPage()
                    p.setFont(ARABIC_FONT, font_size)
                    y = height - margin - line_height * 2 # بدء صفحة جديدة
                
                p.drawInlineImage(img, width - margin - img_w, y - img_h, width=img_w, height=img_h)
                y -= img_h + line_height
            except Exception as e:
                p.setFillColor(colors.red)
                p.drawRightString(x, y, f"❌ خطأ في عرض الصورة: {e}")
                y -= line_height
                p.setFillColor(colors.black)

    # التحليل حسب الترتيب
    draw_analysis_section("PRNU (تحليل ضوضاء الكاميرا)", 
                          analysis_data['prnu_score'], 
                          analysis_data['prnu_verdict'], 
                          analysis_data['prnu_img_base64'])
                          
    draw_analysis_section("ELA (تحليل مستوى الخطأ)", 
                          analysis_data['ela_score'], 
                          analysis_data['ela_verdict'], 
                          analysis_data['ela_img_base64'])

    draw_analysis_section("AI/GradCAM (الذكاء الاصطناعي)", 
                          analysis_data['ai_score'], 
                          analysis_data['ai_verdict'], 
                          analysis_data['gradcam_img_base64'])
                          
    # 7. الصورة الأصلية في نهاية التقرير
    if analysis_data['original_img_base64']:
        p.showPage() # صفحة جديدة للصورة الأصلية
        y = height - margin
        p.setFont(ARABIC_FONT, 14)
        p.drawRightString(x, y, "ج. الصورة الأصلية المرسلة للتحليل")
        y -= line_height * 2
        
        try:
            img_data = base64.b64decode(analysis_data['original_img_base64'])
            img_stream = io.BytesIO(img_data)
            img = ImageReader(img_stream)
            
            # تحجيم الصورة لتناسب عرض الصفحة (بحد أقصى)
            img_w, img_h = width - 2 * margin, (width - 2 * margin) * (img.getSize()[1] / img.getSize()[0])
            
            # رسم الصورة في منتصف الصفحة
            p.drawInlineImage(img, margin, y - img_h, width=img_w, height=img_h)
            y -= img_h
        except Exception as e:
            p.setFillColor(colors.red)
            p.drawRightString(x, y, f"❌ خطأ في عرض الصورة الأصلية: {e}")
            
    # 8. حفظ التقرير وإرجاعه
    p.save()
    buffer.seek(0)
    
    # إرجاع ملف PDF للمتصفح
    return send_file(buffer, as_attachment=True, download_name='Sidq_Report.pdf', mimetype='application/pdf')


# =========================================================
# 5. نقاط نهاية خدمة الملفات الثابتة والصفحات
# =========================================================

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/abshr_security_demo.html')
def abshr_demo_page():
    return send_file('abshr_security_demo.html')

@app.route('/<path:filename>')
def serve_static(filename):
    if os.path.exists(filename):
        return send_file(filename)
    else:
        return "404 Not Found", 404

# =========================================================
# 6. تشغيل التطبيق
# =========================================================

if __name__ == '__main__':
    # يجب تشغيل هذا الخادم في وضع التشغيل (Debug=True) في العرض التقديمي
    # In a production environment, this should be False
    app.run(debug=True, port=5000)