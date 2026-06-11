import os 
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from modules.appFileHandler import resource_path

pygame.mixer.init() 

def play_sound(path, volume = 0.5):
    ''' defaults to static/assets '''
    full_path = resource_path(f"static/assets/{path}")
    sound_effect = pygame.mixer.Sound(full_path)
    sound_effect.set_volume(volume)
    sound_effect.play()
    print("played", path)