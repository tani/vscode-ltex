#!/usr/bin/python3

import argparse
import glob
import json
import os
import re
import shlex
import subprocess



toolsDirPath = os.path.dirname(os.path.abspath(__file__))



def removeKeyIfPresent(d, key):
  if key in d: del d[key]



def run(cmd, **kwargs):
  print("Running {}...".format(" ".join(shlex.quote(x) for x in cmd)))
  return subprocess.run(cmd, stdout=subprocess.PIPE, cwd=toolsDirPath)

def fetchLanguages(toolsDirPath, ltexLsPath):
  classPath = os.pathsep.join([toolsDirPath, os.path.join(ltexLsPath, "lib", "*")])
  run(["javac", "-cp", classPath, "LanguageToolLanguageLister.java"])
  process = run(["java", "-cp", classPath, "LanguageToolLanguageLister"])
  stdout = process.stdout.decode()
  languages = sorted([dict(zip(("languageShortCode", "languageName"), line.split(";")))
      for line in stdout.splitlines()], key=lambda x: x["languageShortCode"])
  languageShortCodes = [x["languageShortCode"] for x in languages]
  languageNames = [x["languageName"] for x in languages]
  return languageShortCodes, languageNames



def main():
  parser = argparse.ArgumentParser(description="Fetches all supported language codes from "
      "LanguageTool and updates the language-specific parts of package.json accordingly")
  parser.add_argument("--ltex-ls-path", default="lib/ltex-ls-*",
      help="path to ltex-ls relative from the root directory of LTeX, supports wildcards")
  args = parser.parse_args()

  ltexPath = os.path.abspath(os.path.join(toolsDirPath, ".."))
  ltexLsPaths = glob.glob(os.path.join(ltexPath, args.ltex_ls_path))
  assert len(ltexLsPaths) > 0, "ltex-ls not found"
  assert len(ltexLsPaths) < 2, "multiple ltex-ls found via wildcard"
  ltexLsPath = ltexLsPaths[0]
  print("Using ltex-ls from {}".format(ltexLsPath))

  print("Fetching languages from LanguageTool...")
  languageShortCodes, languageNames = fetchLanguages(toolsDirPath, ltexLsPath)
  assert len(languageShortCodes) > 0, "No languages found."
  print("Languages: {}".format(", ".join(languageShortCodes)))

  print("Updating package.json...")
  packageJsonPath = os.path.join(ltexPath, "package.json")
  with open(packageJsonPath, "r") as f: packageJson = json.load(f)
  settings = packageJson["contributes"]["configuration"]["properties"]

  settings["ltex.language"]["enum"] = languageShortCodes
  settings["ltex.language"]["enumDescriptions"] = languageNames

  removeKeyIfPresent(settings["ltex.dictionary"], "propertyNames")
  settings["ltex.dictionary"]["properties"] = {
        languageShortCode: {
          "type": "array",
          "items": {
            "type": "string",
          },
          "markdownDescription": "List of additional `{0}` ({1}) words that should not be "
            "counted as spelling errors.".format(languageShortCode, languageName),
          "description": "List of additional '{0}' ({1}) words that should not be "
            "counted as spelling errors.".format(languageShortCode, languageName),
        }
        for languageShortCode, languageName in zip(languageShortCodes, languageNames)
      }

  removeKeyIfPresent(settings["ltex.disabledRules"], "propertyNames")
  settings["ltex.disabledRules"]["properties"] = {
        languageShortCode: {
          "type": "array",
          "items": {
            "type": "string",
          },
          "markdownDescription": "List of additional `{0}` ({1}) rules that should be "
            "disabled (if enabled by default by LanguageTool).".format(languageShortCode, languageName),
          "description": "List of additional '{0}' ({1}) rules that should be "
            "disabled (if enabled by default by LanguageTool).".format(languageShortCode, languageName),
        }
        for languageShortCode, languageName in zip(languageShortCodes, languageNames)
      }

  removeKeyIfPresent(settings["ltex.enabledRules"], "propertyNames")
  settings["ltex.enabledRules"]["properties"] = {
        languageShortCode: {
          "type": "array",
          "items": {
            "type": "string",
          },
          "markdownDescription": "List of additional `{0}` ({1}) rules that should be "
            "enabled (if disabled by default by LanguageTool).".format(languageShortCode, languageName),
          "description": "List of additional '{0}' ({1}) rules that should be "
            "enabled (if disabled by default by LanguageTool).".format(languageShortCode, languageName),
        }
        for languageShortCode, languageName in zip(languageShortCodes, languageNames)
      }

  for settingName in list(settings.keys()):
    if (re.match("^ltex\.languageSettings\.", settingName) or
          re.match("^ltex\.([^\.]+)\.(dictionary|enabledRules|disabledRules)", settingName)):
      del settings[settingName]

  for languageShortCode, languageName in zip(languageShortCodes, languageNames):
    for settingSubName in ["dictionary", "enabledRules", "disabledRules"]:
      metaVariable = ("WORD" if settingSubName == "dictionary" else "RULE")
      settings["ltex.{}.{}".format(languageShortCode, settingSubName)] = {
            "type": "array",
            "scope": "resource",
            "default": [],
            "markdownDeprecationMessage": "**Deprecated:** This setting has been renamed. Use "
                "`\"ltex.{0}\": {{\"{1}\": [\"<{2}1>\", \"<{2}2>\", ...]}}` instead.".format(
                  settingSubName, languageShortCode, metaVariable),
            "deprecationMessage": "Deprecated: This setting has been renamed. Use "
                "'\"ltex.{0}\": {{\"{1}\": [\"<{2}1>\", \"<{2}2>\", ...]}}' instead.".format(
                  settingSubName, languageShortCode, metaVariable),
          }

  with open(packageJsonPath, "w") as f:
    json.dump(packageJson, f, indent=2, ensure_ascii=False)
    f.write("\n")



if __name__ == "__main__":
  main()