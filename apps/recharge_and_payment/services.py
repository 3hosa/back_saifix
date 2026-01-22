import requests
import json
from django.conf import settings

class AlzajilClient:
    """
    عميل للتفاعل مع واجهة برمجة تطبيقات الزاجل (Alzajil Utility Payment Service).
    بناءً على وثائق 'alzajil (Utility Payment Service) v1.12'.
    """

    def __init__(self):
        # يجب أن تكون الإعدادات موجودة في ملف settings الخاص بـ Django
        # استخدام قيم افتراضية أو رفع خطأ إذا لم يتم التكوين
        self.base_url = getattr(settings, 'ALZAJIL_BASE_URL', 'http://localhost/api/tp/v1')
        self.username = getattr(settings, 'ALZAJIL_USERNAME', '')
        self.security_token = getattr(settings, 'ALZAJIL_TOKEN', '')
        self.agent_user_id = getattr(settings, 'ALZAJIL_AGENT_USER_ID', '') # معامل USR

    def _send_request(self, params, method='GET', body=None):
        """
        دالة مساعدة لإرسال الطلبات إلى API.
        تشير الوثائق إلى أن 'Payment Message' تكون عبر POST مع جسم JSON.
        الاستعلام عن الرصيد/العروض/حالة المعاملة عادة ما تكون GET.
        """
        
        # إضافة المعاملات المشتركة إذا لم تكن موجودة
        if self.agent_user_id and 'USR' not in params:
            params['USR'] = self.agent_user_id
        if self.security_token and 'TKN' not in params:
            params['TKN'] = self.security_token

        try:
            if method.upper() == 'POST':
                # بالنسبة للدفع (AC=7100، إلخ)، تقول الوثائق:
                # الطريقة: POST
                # الجسم: سلسلة JSON تحتوي على جميع الحقول أدناه.
                response = requests.post(self.base_url, json=body, params=params)
            else:
                response = requests.get(self.base_url, params=params)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # معالجة أخطاء الاتصال
            return {
                'RC': -100, # استخدام -100 كرمز خطأ عام للخدمة
                'MSG': f'خطأ في الاتصال: {str(e)}'
            }
        except json.JSONDecodeError:
             return {
                'RC': -1,
                'MSG': 'استجابة JSON غير صالحة من المزود'
            }

    def send_payment(self, data):
        """
        AC: 7100 (سداد)، 7200 (عروض)، 7600 (جملة)، 7700 (ترفيه)
        الحقول المتوقعة في data: AC, SC, AMT, SNO, REF, SAC, إلخ.
        """
        # نقطة نهاية الدفع تستخدم POST بناءً على PDF
        
        payload = data.copy()
        payload['USR'] = self.agent_user_id
        payload['TKN'] = self.security_token
        
        # التأكد من مرور الحقول الجديدة إذا كانت موجودة
        # (serializers.py ستقوم بتمريرها تلقائياً إذا كانت في validated_data)
        
        return self._send_request(params={}, method='POST', body=payload)

    def query_subscriber_balance(self, service_code, subscriber_no):
        """
        AC: 4001 (الاستعلام عن رصيد المشترك)
        الطريقة: GET
        معاملات الاستعلام: AC, SC, SNO, USR, TKN
        """
        params = {
            'AC': 4001,
            'SC': service_code,
            'SNO': subscriber_no,
            'USR': self.agent_user_id,
            'TKN': self.security_token
        }
        return self._send_request(params=params, method='GET')

    def manage_offers(self, action_code, service_code, subscriber_no, offer_id=None):
        """
        AC: 4002-4007 (إدارة العروض)
        الطريقة: GET
        """
        params = {
            'AC': action_code,
            'SC': service_code,
            'SNO': subscriber_no,
            'USR': self.agent_user_id,
            'TKN': self.security_token
        }
        if offer_id:
            params['SAC'] = offer_id
            
        return self._send_request(params=params, method='GET')

    def query_agent_balance(self):
        """
        AC: 7400 (الاستعلام عن رصيد الوكيل)
        الطريقة: GET
        """
        params = {
            'AC': 7400,
            'USR': self.agent_user_id,
            'TKN': self.security_token
        }
        return self._send_request(params=params, method='GET')

    def check_transaction_status(self, trans_ref):
        """
        AC: 1003 (التحقق من حالة المعاملة)
        """
        params = {
            'AC': 1003,
            'REF': trans_ref,
            'USR': self.agent_user_id,
            'TKN': self.security_token
        }
        return self._send_request(params=params, method='GET')
