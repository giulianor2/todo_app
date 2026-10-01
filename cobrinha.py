import pygame
import random

pygame.init()
tela = pygame.display.set_mode((600, 400))
relogio = pygame.time.Clock()
T = 20
GRAMA = (162, 209, 73)
inicio = [pygame.Rect(x, 200, T, T) for x in (80, 60, 40)]
cobra = inicio.copy()
direcao = (1, 0)
comida = pygame.Rect(400, 200, T, T)
pontos = 0
fonte = pygame.font.Font(None, 40)
setas = {
    pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0),
    pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1),
}

rodando = True
while rodando:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False
        if evento.type == pygame.KEYDOWN:
            nova = setas.get(evento.key, direcao)
            if nova != (-direcao[0], -direcao[1]):
                direcao = nova

    dx, dy = direcao
    cabeca = cobra[0].move(dx * T, dy * T)
    fora = not tela.get_rect().contains(cabeca)
    if fora or cabeca.collidelist(cobra) >= 0:
        cobra = inicio.copy()
        direcao = (1, 0)
        pontos = 0
        continue
    cobra.insert(0, cabeca)
    if cabeca == comida:
        pontos += 1
        x = random.randrange(0, 600, T)
        y = random.randrange(40, 400, T)
        comida = pygame.Rect(x, y, T, T)
    else:
        cobra.pop()

    tela.fill((170, 215, 81))
    for x in range(0, 600, T):
        for y in range(x % 40, 400, 40):
            pygame.draw.rect(tela, GRAMA, (x, y, T, T))
    placar = fonte.render(f"Pontos: {pontos}", 1, "white")
    tela.blit(placar, (10, 10))
    for parte in cobra:
        pygame.draw.rect(tela, "royalblue", parte, 0, 6)
    pygame.draw.circle(tela, "red", comida.center, 9)
    pygame.display.flip()
    relogio.tick(10)

pygame.quit()
