import requests
import time
import random
import numpy as np
import json
import os
import logging
from datetime import datetime
from collections import deque
from fake_useragent import UserAgent
from pathlib import Path

# ======= CONFIGURATION GLOBALE =======
CONFIG = {
    # Identifiants waitlist
    "WAITLIST_ID": 25431,
    "WAITLIST_KEY": "A4PGKD",
    "MAIN_REFERRAL_TOKEN": "QI1ISZOQ5",
    
    # Configuration emails
    "BASE_EMAIL": "genie-{}@lenylvt.cc",
    "REFERENCE_EMAIL": "leny.levant95@icloud.com",  # Email de référence pour vérifier la position
    "START_EMAIL": 40,  # Numéro de départ pour les emails
    "STOP_EMAIL": 50,   # Numéro de fin pour les emails
    
    # URLs
    "SIGNUP_URL": "https://api.getwaitlist.com/api/v1/signup",
    "CHECK_URL": "https://api.getwaitlist.com/api/v1/signup",
    
    # Délais
    "CHECK_DELAY": 5,  # Délai en secondes entre POST et vérification
    
    # Fichiers
    "DATA_FOLDER": "./data",
    "DATA_FILENAME": "waitlist_ai_data.json"
}

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("waitlist-ai")

# Création du dossier de données
DATA_FOLDER = Path(CONFIG["DATA_FOLDER"])
DATA_FILE = DATA_FOLDER / CONFIG["DATA_FILENAME"]
DATA_FOLDER.mkdir(exist_ok=True)
logger.info(f"📁 Dossier de données: {DATA_FOLDER.absolute()}")
logger.info(f"📄 Fichier de données: {DATA_FILE.absolute()}")

# ======= CLASSE D'INTELLIGENCE ARTIFICIELLE =======
class WaitlistAI:
    def __init__(self, initial_min_delay=5, initial_max_delay=10, history_size=10):
        self.min_delay = initial_min_delay
        self.max_delay = initial_max_delay
        self.history = deque(maxlen=history_size)
        self.spam_count = 0
        self.success_count = 0
        self.total_count = 0
        self.user_agents = []
        self.referral_variations = [
            f"https://geniegetsme.com/waitlist?ref_id={CONFIG['MAIN_REFERRAL_TOKEN']}",
            f"https://geniegetsme.com/waitlist?ref_id={CONFIG['MAIN_REFERRAL_TOKEN']}&source=email",
            f"https://geniegetsme.com/waitlist?ref_id={CONFIG['MAIN_REFERRAL_TOKEN']}&utm_source=direct",
            f"https://www.geniegetsme.com/waitlist?ref_id={CONFIG['MAIN_REFERRAL_TOKEN']}",
        ]
        self.current_params = {
            "waitlist_id": CONFIG["WAITLIST_ID"],
            "referral_idx": 0,
            "user_agent_idx": 0,
            "delay_strategy": "random",  # random, fixed, increasing
        }
        
        # Charger les données sauvegardées si elles existent
        self.load_data()
        
        # Initialiser les user agents
        self._init_user_agents()
        
    def _init_user_agents(self):
        """Initialise les user agents, utilisant fake_useragent ou des agents prédéfinis"""
        try:
            ua = UserAgent()
            self.user_agents = [
                ua.chrome,
                ua.firefox,
                ua.safari,
                ua.edge,
                ua.random
            ]
        except Exception as e:
            logger.warning(f"🔶 Erreur lors de l'initialisation des user agents: {e}")
            # Fallback avec des user agents statiques
            self.user_agents = [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
            ]
    
    def record_result(self, is_spam, position_info=None):
        """Enregistre le résultat d'une tentative et ajuste les paramètres"""
        self.history.append(1 if is_spam else 0)
        self.total_count += 1
        
        if is_spam:
            self.spam_count += 1
            self._adjust_strategy_after_spam()
        else:
            self.success_count += 1
            self._adjust_strategy_after_success()
            
        # Sauvegarder les données après chaque tentative
        self.save_data()
        logger.info(f"📊 Stats mises à jour: {self.success_count} succès, {self.spam_count} spams")
    
    def _adjust_strategy_after_spam(self):
        """Ajuste la stratégie après détection d'un spam"""
        # Changer de user agent
        self.current_params["user_agent_idx"] = (self.current_params["user_agent_idx"] + 1) % len(self.user_agents)
        
        # Changer de referral
        self.current_params["referral_idx"] = (self.current_params["referral_idx"] + 1) % len(self.referral_variations)
        
        # Augmenter les délais
        self.min_delay = min(self.min_delay * 1.5, 30)
        self.max_delay = min(self.max_delay * 1.5, 60)
        
        # Changer la stratégie de délai
        strategies = ["random", "fixed", "increasing"]
        current_idx = strategies.index(self.current_params["delay_strategy"])
        self.current_params["delay_strategy"] = strategies[(current_idx + 1) % len(strategies)]
        
        logger.info(f"🧠 Changement de stratégie après spam: UA={self.current_params['user_agent_idx']}, "
                   f"REF={self.current_params['referral_idx']}, DÉLAI={self.current_params['delay_strategy']}")
    
    def _adjust_strategy_after_success(self):
        """Ajuste la stratégie après succès"""
        # Si les 3 dernières tentatives ont réussi, réduire les délais
        if len(self.history) >= 3 and sum(list(self.history)[-3:]) == 0:
            self.min_delay = max(self.min_delay * 0.9, 3)
            self.max_delay = max(self.max_delay * 0.9, 5)
            logger.info(f"🧠 Réduction des délais après succès: {self.min_delay:.1f}s-{self.max_delay:.1f}s")
    
    def get_optimal_wait_time(self):
        """Détermine le temps d'attente optimal selon la stratégie actuelle"""
        if self.current_params["delay_strategy"] == "random":
            # Ajouter un peu de bruit pour éviter les motifs prévisibles
            jitter = np.random.normal(0, 1)
            wait_time = random.uniform(self.min_delay, self.max_delay) + jitter
        elif self.current_params["delay_strategy"] == "fixed":
            wait_time = (self.min_delay + self.max_delay) / 2
        elif self.current_params["delay_strategy"] == "increasing":
            # Temps qui augmente progressivement avec le nombre de requêtes
            base_time = (self.min_delay + self.max_delay) / 2
            wait_time = base_time + (self.total_count % 5)
        
        return max(wait_time, 1)  # Au moins 1 seconde d'attente
    
    def get_current_headers(self):
        """Génère les en-têtes HTTP actuels selon la stratégie"""
        user_agent = self.user_agents[self.current_params["user_agent_idx"]]
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
            "Origin": "https://geniegetsme.com",
            "Referer": "https://geniegetsme.com/",
            "DNT": "1"
        }
        
        # Ajouter un en-tête aléatoire pour la variété
        if random.random() > 0.7:
            headers["X-Requested-With"] = "XMLHttpRequest"
        
        return headers
    
    def get_current_referral(self):
        """Renvoie le lien de parrainage actuel"""
        return self.referral_variations[self.current_params["referral_idx"]]
    
    def get_stats(self):
        """Renvoie les statistiques actuelles"""
        if self.total_count == 0:
            return "Aucune statistique disponible"
            
        spam_rate = (self.spam_count / self.total_count) * 100
        success_rate = (self.success_count / self.total_count) * 100
        
        return {
            "spam_rate": f"{spam_rate:.1f}%",
            "success_rate": f"{success_rate:.1f}%",
            "total_attempts": self.total_count,
            "current_strategy": {
                "user_agent": self.current_params["user_agent_idx"],
                "referral": self.current_params["referral_idx"],
                "delay": self.current_params["delay_strategy"],
                "min_delay": f"{self.min_delay:.1f}s",
                "max_delay": f"{self.max_delay:.1f}s"
            }
        }
    
    def save_data(self):
        """Sauvegarde les données d'apprentissage dans un fichier JSON"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "min_delay": self.min_delay,
            "max_delay": self.max_delay,
            "spam_count": self.spam_count,
            "success_count": self.success_count,
            "total_count": self.total_count,
            "current_params": self.current_params,
            "history": list(self.history)
        }
        
        try:
            # S'assurer que le dossier existe
            DATA_FOLDER.mkdir(exist_ok=True)
            
            # Écrire les données
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Données sauvegardées dans {DATA_FILE}")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde des données: {e}")
    
    def load_data(self):
        """Charge les données d'apprentissage depuis un fichier JSON"""
        if not os.path.exists(DATA_FILE):
            logger.info("📂 Aucune donnée antérieure trouvée")
            return
            
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                
            self.min_delay = data.get("min_delay", self.min_delay)
            self.max_delay = data.get("max_delay", self.max_delay)
            self.spam_count = data.get("spam_count", 0)
            self.success_count = data.get("success_count", 0)
            self.total_count = data.get("total_count", 0)
            self.current_params = data.get("current_params", self.current_params)
            
            # Restaurer l'historique
            history_data = data.get("history", [])
            self.history = deque(history_data, maxlen=self.history.maxlen)
            
            logger.info(f"📂 Données chargées: {self.total_count} tentatives antérieures")
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données: {e}")

# ======= FONCTIONS DE SERVICE =======
def generate_email(number):
    """Génère un email pour le test"""
    email = CONFIG["BASE_EMAIL"].format(number)
    logger.info(f"📧 {email}")
    return email

def check_waitlist_status(email):
    """Vérifie le statut et la position dans la liste d'attente"""
    url = f"{CONFIG['CHECK_URL']}?waitlist_id={CONFIG['WAITLIST_ID']}&email={email}"
    
    try:
        logger.info(f"🔍 Vérification du statut pour {email}...")
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Erreur lors de la vérification: {response.status_code}")
            return None
            
        data = response.json()
        return data
    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification: {str(e)}")
        return None

def check_reference_status():
    """Vérifie le statut de l'email de référence"""
    reference_email = CONFIG["REFERENCE_EMAIL"]
    status = check_waitlist_status(reference_email)
    
    if status:
        logger.info(f"📊 Statut référence ({reference_email}):")
        logger.info(f"   - Parrainage: {status.get('amount_referred', 0)} personnes")
        logger.info(f"   - Position: {status.get('priority', 'N/A')}")
    
    return status

def signup(email, ai):
    """Inscription à la liste d'attente"""
    data = {
        "waitlist_id": CONFIG["WAITLIST_ID"],
        "email": email,
        "referral_link": ai.get_current_referral()
    }
    
    # Ajouter des paramètres aléatoires pour éviter la détection
    if random.random() > 0.7:
        data["source"] = random.choice(["direct", "web", "friend", "social"])
    
    if random.random() > 0.8:
        data["timestamp"] = int(datetime.now().timestamp())
    
    headers = ai.get_current_headers()
    
    logger.info("🔄 Envoi de la requête d'inscription...")
    
    try:
        response = requests.post(
            CONFIG["SIGNUP_URL"], 
            json=data, 
            headers=headers, 
            timeout=15
        )
        
        # En cas d'erreur inattendue
        if response.status_code != 200:
            logger.warning(f"⚠️ Status: {response.status_code}")
            logger.debug(f"Réponse: {response.text}")
            return {"is_spam": True, "error": f"Status {response.status_code}"}
        
        result = response.json()
        return result
    except Exception as e:
        logger.error(f"❌ Erreur lors de la requête: {str(e)}")
        return {"is_spam": True, "error": str(e)}

# ======= FONCTION PRINCIPALE =======
def run_waitlist_loop():
    """Fonction principale qui exécute la boucle d'inscription"""
    # Forcer la création du dossier data
    DATA_FOLDER.mkdir(exist_ok=True, parents=True)
    logger.info(f"Vérification du dossier data: {DATA_FOLDER.exists()}")
    
    # Récupérer les valeurs depuis la configuration
    start = CONFIG["START_EMAIL"]
    stop = CONFIG["STOP_EMAIL"]
    
    # Initialiser l'IA avec des valeurs par défaut (l'IA s'adaptera d'elle-même)
    ai = WaitlistAI(initial_min_delay=5, initial_max_delay=10)
    logger.info(f"🚀 Démarrage du processus pour {stop-start+1} emails ({start}-{stop})")
    
    # Vérifier l'état initial de référence
    initial_ref_status = check_reference_status()
    initial_amount_referred = initial_ref_status.get('amount_referred', 0) if initial_ref_status else 0
    
    logger.info(f"📈 Nombre initial de parrainages: {initial_amount_referred}")
    
    stats = {
        "total": stop-start+1,
        "success": 0,
        "spam": 0,
        "error": 0,
        "initial_amount_referred": initial_amount_referred,
        "final_amount_referred": initial_amount_referred
    }
    
    for i in range(start, stop + 1):
        email = generate_email(i)
        
        # Inscription
        result = signup(email, ai)
        is_spam = result.get("is_spam", False)
        
        if is_spam:
            stats["spam"] += 1
            logger.warning(f"🚫 Spam détecté pour {email}")
        else:
            stats["success"] += 1
            logger.info(f"✅ Inscription réussie pour {email}")
        
        # Attendre le délai obligatoire de 5 secondes
        logger.info(f"⏱️ Attente obligatoire: {CONFIG['CHECK_DELAY']}s")
        time.sleep(CONFIG['CHECK_DELAY'])
        
        # Vérifier le statut après inscription
        status = check_waitlist_status(email)
        
        if status:
            # Log du statut
            priority = status.get('priority', 'N/A')
            logger.info(f"🏆 Position dans la file: {priority}")
            
            # Mise à jour des stats avec la position la plus récente
            if isinstance(priority, (int, float)):
                stats["last_position"] = priority
            
            # Vérifier le statut de référence
            ref_status = check_reference_status()
            current_amount_referred = ref_status.get('amount_referred', 0) if ref_status else stats["initial_amount_referred"]
            
            # Calculer le changement
            referral_change = current_amount_referred - stats["initial_amount_referred"]
            stats["final_amount_referred"] = current_amount_referred
            
            logger.info(f"👥 Parrainages actuels: {current_amount_referred} (+{referral_change} depuis le début)")
        
        # Enregistrer le résultat pour l'IA
        ai.record_result(is_spam, status)
        
        # Ne pas attendre après la dernière requête
        if i < stop:
            wait_time = ai.get_optimal_wait_time()
            logger.info(f"⏱️ Attente IA: {wait_time:.1f}s")
            time.sleep(wait_time)
    
    # Afficher les statistiques à la fin
    logger.info("=" * 50)
    logger.info("📊 RÉSULTATS FINAUX:")
    logger.info(f"✅ Succès: {stats['success']}/{stats['total']} ({stats['success']/stats['total']*100:.1f}%)")
    logger.info(f"🚫 Spam: {stats['spam']}/{stats['total']} ({stats['spam']/stats['total']*100:.1f}%)")
    logger.info(f"👥 Parrainages: {stats['initial_amount_referred']} → {stats['final_amount_referred']} (+{stats['final_amount_referred']-stats['initial_amount_referred']})")
    
    if "last_position" in stats:
        logger.info(f"🏆 Dernière position: {stats['last_position']}")
    
    # Sauvegarder l'état final
    ai.save_data()
    
    # Afficher la stratégie optimale trouvée
    logger.info("🧠 Stratégie optimale:")
    for key, value in ai.get_stats()["current_strategy"].items():
        logger.info(f"   - {key}: {value}")

# ======= POINT D'ENTRÉE =======
if __name__ == "__main__":
    # Assurer que le dossier data existe avant de commencer
    os.makedirs(CONFIG["DATA_FOLDER"], exist_ok=True)
    
    # Exécuter la boucle principale
    run_waitlist_loop()
    
    # Vérifier que le fichier JSON a été créé
    json_file = os.path.join(CONFIG["DATA_FOLDER"], CONFIG["DATA_FILENAME"])
    if os.path.exists(json_file):
        logger.info(f"✅ Fichier JSON créé avec succès: {json_file}")
        logger.info(f"   Taille: {os.path.getsize(json_file)} octets")
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                logger.info(f"   Données valides, dernière mise à jour: {data.get('timestamp', 'N/A')}")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la lecture du fichier JSON: {e}")
    else:
        logger.error(f"❌ Le fichier JSON n'a pas été créé: {json_file}")