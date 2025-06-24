import streamlit as st
import zipfile
import io
import re
from datetime import timedelta

# Templates pour le manifest SCORM 1.2 et SCORM 2004
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

HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
  <title>SCORM Content</title>
  <script src="scorm.js"></script>
  <script>
    let elapsed = 0;
    const requiredTime = {time};

    window.onload = function() {
      pipwerks.SCORM.version = "1.2";
      pipwerks.SCORM.init();

      document.getElementById("target").src = "{url}";

      const timer = setInterval(() => {
        elapsed++;
        const progress = Math.min((elapsed / requiredTime) * 100, 100);

        pipwerks.SCORM.set("cmi.core.score.raw", progress.toFixed(0));
        pipwerks.SCORM.set("cmi.core.lesson_location", elapsed.toString());

        if (elapsed >= requiredTime) {
          pipwerks.SCORM.set("cmi.core.lesson_status", "completed");
          clearInterval(timer);
          pipwerks.SCORM.quit();
        } else {
          pipwerks.SCORM.set("cmi.core.lesson_status", "incomplete");
        }

        pipwerks.SCORM.save();
      }, 1000);
    }
  </script>
</head>
<body>
  <h2>Chargement du contenu...</h2>
  <iframe id="target" width="100%" height="600px" style="border: none;"></iframe>
</body>
</html>
'''

SCORM_JS = '''// pipwerks SCORM API Wrapper (simplifié pour SCORM 1.2)
var pipwerks = {
  SCORM: {
    version: "1.2",
    handleCompletion: true,
    api: null,

    init: function() {
      this.api = this.getAPIHandle();
      if (this.api === null) {
        console.error("SCORM API non trouvée.");
        return false;
      }
      return this.api.LMSInitialize("") === "true";
    },

    get: function(parameter) {
      return this.api ? this.api.LMSGetValue(parameter) : null;
    },

    set: function(parameter, value) {
      return this.api ? this.api.LMSSetValue(parameter, value) === "true" : false;
    },

    save: function() {
      return this.api ? this.api.LMSCommit("") === "true" : false;
    },

    quit: function() {
      return this.api ? this.api.LMSFinish("") === "true" : false;
    },

    getAPIHandle: function() {
      var win = windo
