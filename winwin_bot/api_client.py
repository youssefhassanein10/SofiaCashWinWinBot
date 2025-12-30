import hashlib
import requests
import logging
from datetime import datetime, timezone
from config import Config

logger = logging.getLogger(__name__)

class SofiaCashAPI:
    def __init__(self):
        self.config = Config
        self.base_url = self.config.API_BASE_URL
    
    def _calculate_confirm(self, param_value):
        """Расчет confirm строки"""
        data = f"{param_value}:{self.config.API_HASH}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _generate_signature(self, method, **params):
        """Генерация подписи в зависимости от метода"""
        if method == "balance":
            dt = params.get('dt')
            str_a = f"hash={self.config.API_HASH}&cashierpass={self.config.API_CASHIERPASS}&dt={dt}"
            hash_a = hashlib.sha256(str_a.encode()).hexdigest()
            
            str_b = f"dt={dt}&cashierpass={self.config.API_CASHIERPASS}&cashdeskid={self.config.API_CASHDESKID}"
            hash_b = hashlib.md5(str_b.encode()).hexdigest()
            
            combined = hash_a + hash_b
            return hashlib.sha256(combined.encode()).hexdigest()
        
        elif method == "find_user":
            user_id = params.get('user_id')
            str_a = f"hash={self.config.API_HASH}&userid={user_id}&cashdeskid={self.config.API_CASHDESKID}"
            hash_a = hashlib.sha256(str_a.encode()).hexdigest()
            
            str_b = f"userid={user_id}&cashierpass={self.config.API_CASHIERPASS}&hash={self.config.API_HASH}"
            hash_b = hashlib.md5(str_b.encode()).hexdigest()
            
            combined = hash_a + hash_b
            return hashlib.sha256(combined.encode()).hexdigest()
        
        elif method == "deposit":
            user_id = params.get('user_id')
            amount = params.get('amount')
            lng = params.get('lng', 'ru')
            
            str_a = f"hash={self.config.API_HASH}&lng={lng}&UserId={user_id}"
            hash_a = hashlib.sha256(str_a.encode()).hexdigest()
            
            str_b = f"summa={amount}&cashierpass={self.config.API_CASHIERPASS}&cashdeskid={self.config.API_CASHDESKID}"
            hash_b = hashlib.md5(str_b.encode()).hexdigest()
            
            combined = hash_a + hash_b
            return hashlib.sha256(combined.encode()).hexdigest()
        
        elif method == "payout":
            user_id = params.get('user_id')
            code = params.get('code')
            lng = params.get('lng', 'ru')
            
            str_a = f"hash={self.config.API_HASH}&lng={lng}&UserId={user_id}"
            hash_a = hashlib.sha256(str_a.encode()).hexdigest()
            
            str_b = f"code={code}&cashierpass={self.config.API_CASHIERPASS}&cashdeskid={self.config.API_CASHDESKID}"
            hash_b = hashlib.md5(str_b.encode()).hexdigest()
            
            combined = hash_a + hash_b
            return hashlib.sha256(combined.encode()).hexdigest()
    
    def get_balance(self):
        """Получение баланса кассы"""
        dt = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
        confirm = self._calculate_confirm(self.config.API_CASHDESKID)
        signature = self._generate_signature("balance", dt=dt)
        
        url = f"{self.base_url}Cashdesk/{self.config.API_CASHDESKID}/Balance"
        params = {
            "confirm": confirm,
            "dt": dt
        }
        headers = {"sign": signature}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка баланса: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Ошибка запроса баланса: {e}")
            return None
    
    def find_user(self, user_id):
        """Поиск игрока в системе Winwin"""
        confirm = self._calculate_confirm(user_id)
        signature = self._generate_signature("find_user", user_id=user_id)
        
        url = f"{self.base_url}Users/{user_id}"
        params = {
            "confirm": confirm,
            "cashdeskId": self.config.API_CASHDESKID
        }
        headers = {"sign": signature}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка поиска пользователя: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Ошибка запроса пользователя: {e}")
            return None
    
    def deposit_to_user(self, user_id, amount):
        """Пополнение счета игрока через SofiaCash"""
        confirm = self._calculate_confirm(user_id)
        signature = self._generate_signature("deposit", user_id=user_id, amount=amount)
        
        url = f"{self.base_url}Deposit/{user_id}/Add"
        headers = {
            "sign": signature,
            "Content-Type": "application/json"
        }
        payload = {
            "cashdeskId": int(self.config.API_CASHDESKID),
            "lng": "ru",
            "summa": float(amount),
            "confirm": confirm
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return {
                        'success': True,
                        'amount': result.get('summa'),
                        'message': result.get('message', 'Успешно')
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', 'Неизвестная ошибка'),
                        'message_id': result.get('messageId')
                    }
            else:
                return {
                    'success': False,
                    'error': f"HTTP ошибка: {response.status_code}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def payout_from_user(self, user_id, code):
        """Выплата со счета игрока"""
        confirm = self._calculate_confirm(user_id)
        signature = self._generate_signature("payout", user_id=user_id, code=code)
        
        url = f"{self.base_url}Deposit/{user_id}/Payout"
        headers = {
            "sign": signature,
            "Content-Type": "application/json"
        }
        payload = {
            "cashdeskId": int(self.config.API_CASHDESKID),
            "lng": "ru",
            "code": code,
            "confirm": confirm
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {'success': False, 'error': f"HTTP ошибка: {response.status_code}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}
