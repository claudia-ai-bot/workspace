#!/usr/bin/env python3
"""
Hello World in 5 Random Languages
"""

import random

# Language: "Hello World" translation
LANGUAGES = {
    "English": "Hello World",
    "Spanish": "Hola Mundo",
    "French": "Bonjour le monde",
    "German": "Hallo Welt",
    "Italian": "Ciao Mondo",
    "Portuguese": "Olá Mundo",
    "Japanese": "こんにちは世界",
    "Korean": "안녕하세요 세계",
    "Chinese": "你好世界",
    "Russian": "Привет мир",
    "Arabic": "مرحبا بالعالم",
    "Hindi": "नमस्ते दुनिया",
    "Turkish": "Merhaba Dünya",
    "Vietnamese": "Xin chào thế giới",
    "Polish": "Cześć świecie",
    "Dutch": "Hallo Wereld",
    "Greek": "Γeia σας κόσμε",
    "Swedish": "Hej världen",
    "Thai": "สวัสดีชาวโลก",
    "Finnish": "Terve maailma",
}

def main():
    # Pick 5 random languages
    selected = random.sample(list(LANGUAGES.items()), 5)
    
    print("🌍 Hello World in 5 Random Languages:\n")
    for i, (lang, greeting) in enumerate(selected, 1):
        print(f"{i}. {lang}: {greeting}")

if __name__ == "__main__":
    main()
