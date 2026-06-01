import os 
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame


pygame.mixer.init() 

default_path = "static/assets"
def play_sound(path, volume = 0.5):
    ''' defaults to static/assets btw '''

    path = "/".join([default_path, path])

    sound_effect = pygame.mixer.Sound(path)
    sound_effect.set_volume(volume)
    sound_effect.play()