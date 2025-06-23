import streamlit as st
import zipfile
import io
from datetime import timedelta

# Templates pour le manifest SCORM 1.2 et SCORM 2004
# MANIFEST_12 définit la structure XML pour un paquet SCORM 1.2.
# Il spécifie l'organisation par défaut, le titre du module,
# et les ressources incluses (index.html et scorm.js).
MANIFEST_12 = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="com.example.scorm" version="1.0"
          xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2
          imscp_rootv1p1p2.xsd">
  <organizations default="ORG">
    <organization identifier="ORG">
      <title>SCORM Module</title>
      <item identifier="ITEM" identifierref="RES">
        <title>SCORM URL Content</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES" type="webcontent" adlcp:scormtype="sco" href="index.html">
      <file href="index.html"/>
      <file href="scorm.js"/>
    </resource>
  </resources>
</manifest>
'''

# MANIFEST_2004 définit la structure XML pour un paquet SCORM 2004.
# Similaire à MANIFEST_12 mais utilise le schéma 2004 et une version différente.
MANIFEST_2004 = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="com.example.scorm" version="1.0"
          xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd">
  <organizations default="ORG">
    <organization identifier="ORG">
      <title>SCORM Module</title>
      <item identifier="ITEM" identifierref="RES">
        <title>SCORM URL Content</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES" type="webcontent" adlcp:scormType="sco" href="index.html">
      <file href="index.html"/>
      <file href="scorm.js"/>
    </resource>
  </resources>
</manifest>
'''

# HTML_TEMPLATE contient la structure HTML de base pour le contenu SCORM.
# Il inclut un script pour la gestion du SCORM et un iframe pour charger l'URL externe.
# Les placeholders {url} et {time} seront remplacés dynamiquement.
HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
  <title>SCORM Content</title>
  <script src="scorm.js"></script>
  <script>
    let elapsed = 0; // Temps écoulé en secondes
    const requiredTime = {time}; // Temps minimal requis pour la complétion

    window.onload = function() {
      // Initialisation du wrapper SCORM pipwerks
      pipwerks.SCORM.version = "1.2"; // Spécifie la version SCORM (pour ce simple wrapper)
      pipwerks.SCORM.init(); // Initialise la connexion avec le LMS
      
      // Charge l'URL cible dans l'iframe
      document.getElementById("target").src = "{url}";

      // Met en place une minuterie pour suivre le temps passé et mettre à jour le LMS
      const timer = setInterval(() => {
        elapsed++; // Incrémente le temps écoulé
        // Calcule le progrès en pourcentage, plafonné à 100%
        const progress = Math.min((elapsed / requiredTime) * 100, 100);

        // Met à jour le score brut (score de 0 à 100)
        pipwerks.SCORM.set("cmi.core.score.raw", progress.toFixed(0));
        // Met à jour la localisation de la leçon avec le temps écoulé
        pipwerks.SCORM.set("cmi.core.lesson_location", elapsed.toString());

        // Met à jour le statut de la leçon
        if (elapsed >= requiredTime) {
          pipwerks.SCORM.set("cmi.core.lesson_status", "completed"); // Marque comme complété si le temps requis est atteint
          // Optionnel : Arrêter le timer une fois le temps requis atteint pour éviter les mises à jour inutiles
          clearInterval(timer);
          pipwerks.SCORM.quit(); // Quitter la connexion SCORM si tout est complété
        } else {
          pipwerks.SCORM.set("cmi.core.lesson_status", "incomplete"); // Sinon, marque comme incomplet
        }

        pipwerks.SCORM.save(); // Enregistre les données dans le LMS
      }, 1000); // Exécute toutes les secondes (1000 ms)
    }
  </script>
</head>
<body>
  <h2>Chargement du contenu...</h2>
  <iframe id="target" width="100%" height="600px" style="border: none;"></iframe>
</body>
</html>
'''

# SCORM_JS est une version simplifiée du wrapper pipwerks SCORM API.
# Il fournit les fonctions de base pour interagir avec un LMS (Initialize, GetValue, SetValue, Commit, Finish).
SCORM_JS = '''// pipwerks SCORM API Wrapper (simplifié pour SCORM 1.2)
var pipwerks = {
  SCORM: {
    version: "1.2", // Version SCORM gérée par ce wrapper
    handleCompletion: true, // Non utilisé dans cette version simplifiée
    api: null, // Référence à l'API du LMS

    // Initialise la connexion avec le LMS
    init: function() {
      this.api = this.getAPIHandle(); // Tente d'obtenir le handle de l'API LMS
      if (this.api === null) {
        console.error("SCORM API non trouvée.");
        return false;
      }
      // Appelle LMSInitialize pour commencer la session SCORM
      return this.api.LMSInitialize("") === "true";
    },

    // Récupère une valeur du LMS
    get: function(parameter) {
      return this.api ? this.api.LMSGetValue(parameter) : null;
    },

    // Définit une valeur dans le LMS
    set: function(parameter, value) {
      return this.api ? this.api.LMSSetValue(parameter, value) === "true" : false;
    },

    // Enregistre les données dans le LMS
    save: function() {
      return this.api ? this.api.LMSCommit("") === "true" : false;
    },

    // Termine la connexion avec le LMS
    quit: function() {
      return this.api ? this.api.LMSFinish("") === "true" : false;
    },

    // Recherche et renvoie le handle de l'API SCORM dans la fenêtre parent ou courante
    getAPIHandle: function() {
      var win = window;
      while (win) {
        // Vérifie si l'objet 'API' existe
        if (win.API) return win.API;
        // Si non, et s'il y a un parent différent de la fenêtre actuelle, remonte d'un niveau
        if (win.parent && win.parent !== win) win = win.parent;
        else break; // S'il n'y a plus de parent ou si c'est la fenêtre elle-même, arrête la recherche
      }
      return null; // Si l'API n'est pas trouvée
    }
  }
};
'''

# --- Streamlit App ---
st.title("Générateur de paquet SCORM")

# Champ de saisie pour l'URL à encapsuler
url = st.text_input("URL à consulter", "https://example.com")
# Sélecteur pour choisir la version SCORM
scorm_version = st.selectbox("Version SCORM", ["SCORM 1.2", "SCORM 2004 3rd edition"])

st.subheader("Durée minimale de consultation")
# Utilisation de colonnes pour une meilleure disposition des champs de durée
col_h, col_m, col_s = st.columns(3)

with col_h:
    hours = st.number_input("Heures", min_value=0, value=0)
with col_m:
    minutes = st.number_input("Minutes", min_value=0, max_value=59, value=0)
with col_s:
    seconds = st.number_input("Secondes", min_value=0, max_value=59, value=30)

# Calcul de la durée totale en secondes
total_duration_in_seconds = (hours * 3600) + (minutes * 60) + seconds

# Bouton pour générer le paquet SCORM
if st.button("Générer le SCORM"):
    if total_duration_in_seconds == 0:
        st.error("La durée minimale de consultation doit être supérieure à zéro.")
    else:
        # Créer un buffer en mémoire pour le fichier zip
        buffer = io.BytesIO()
        # Crée un fichier zip en mémoire
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Remplace les placeholders dans le template HTML avec l'URL et la durée
            html_content = HTML_TEMPLATE.replace("{url}", url).replace("{time}", str(total_duration_in_seconds))
            # Écrit le fichier index.html dans le zip
            zf.writestr("index.html", html_content)
            # Écrit le fichier scorm.js dans le zip
            zf.writestr("scorm.js", SCORM_JS)

            # Choisit le bon manifeste SCORM en fonction de la version sélectionnée
            if scorm_version == "SCORM 1.2":
                zf.writestr("imsmanifest.xml", MANIFEST_12)
            else:
                zf.writestr("imsmanifest.xml", MANIFEST_2004)

        # Affiche un message de succès
        st.success("Fichier SCORM généré !")
        # Fournit un bouton de téléchargement pour le fichier zip généré
        st.download_button(
            "📥 Télécharger le paquet SCORM",
            data=buffer.getvalue(),
            file_name="scorm_package.zip",
            mime="application/zip" # Spécifie le type MIME pour le téléchargement
        )
