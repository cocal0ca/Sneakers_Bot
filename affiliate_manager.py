import urllib.parse
from config import AFFILIATE_NETWORKS


class AffiliateManager:
    def __init__(self, networks=None):
        """
        :param networks: Словарь конфигурации сетей. Если None, берется из config.py
        """
        self.networks = networks if networks is not None else AFFILIATE_NETWORKS

    def convert_link(self, original_url, source_name):
        """
        Превращает обычную ссылку в партнерскую (DeepLink).

        :param original_url: Исходная ссылка на товар
        :param source_name: Название магазина (ключ в конфиге), например 'StreetBeat'
        :return: Партнерская ссылка или исходная, если нет конфига
        """
        if not original_url or not source_name:
            return original_url

        network_config = self.networks.get(source_name)

        # Если для этого источника нет настроек или не задан base_url
        if not network_config or not network_config.get("base_url"):
            return original_url

        try:
            net_type = network_config.get("type", "custom").lower()
            base_url = network_config["base_url"]

            # Кодируем исходную ссылку (важно для параметров URL)
            encoded_url = urllib.parse.quote(original_url)

            if net_type == "admitad":
                # Admitad Deeplink: base_url + encoded_target_url
                # Обычно base_url заканчивается на ?ulp= или &ulp= (или просто /)
                # Если в base_url нет ulp=, можно попробовать добавить.
                # Но для универсальности лучше полагать, что юзер вставил правильную ссылку-генератор.
                # Часто формат: https://ad.admitad.com/g/xyz/?ulp={url}&subid={subid}

                # Простая склейка, если юзер указал base_url заканчивающийся на =
                return f"{base_url}{encoded_url}"

            elif net_type == "actionpay":
                # Actionpay: обычно тоже base_url + url
                return f"{base_url}{encoded_url}"

            else:
                # Custom: простая конкатенация
                return f"{base_url}{encoded_url}"

        except Exception as e:
            print(f"Ошибка при конвертации CPA ссылки для {source_name}: {e}")
            return original_url
