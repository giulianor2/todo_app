import random
import pygame

pygame.init()
tela = pygame.display.set_mode((600, 400))
relogio = pygame.time.Clock()
fonte = pygame.font.Font(None, 30)
estrelas = [(random.randint(0, 599),
             random.randint(0, 399)) for _ in range(60)]

def sprite(desenho, cor):
    img = pygame.Surface((len(desenho[0]) * 3,
                          len(desenho) * 3),
                         pygame.SRCALPHA)
    for y, linha in enumerate(desenho):
        for x, c in enumerate(linha):
            if c == "#":
                img.fill(cor, (x * 3, y * 3, 3, 3))
    return img

nave = sprite(["......#......",
               ".....###.....",
               ".###########.",
               "#############",
               "#############"], (80, 230, 120))
x = 300
tiro = None
cores = ["#ff5c8a", "#b07cff", "#5cd6ff", "#ffd75c"]
imagens = [sprite(["..#.....#..",
                   "...#...#...",
                   "..#######..",
                   ".##.###.##.",
                   "###########",
                   "#.#######.#",
                   "#.#.....#.#",
                   "...##.##..."], cor) for cor in cores]

def onda():
    return [(pygame.Rect(60 + c * 50, 40 + l * 34,
                         33, 24), imagens[l])
            for l in range(4) for c in range(8)]

aliens = onda()
lado = 1
explosao = sprite(["#...#...#",
                   ".#..#..#.",
                   "..#...#..",
                   "##.....##",
                   "..#...#..",
                   ".#..#..#.",
                   "#...#...#"], "orange")
boom = None
boom_t = 0
pontos = 0
bombas = []
vidas = 3
choque = 0

rodando = True
while rodando:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_SPACE and not tiro:
                tiro = pygame.Rect(x - 2, 340, 4, 14)

    teclas = pygame.key.get_pressed()
    x += (teclas[pygame.K_RIGHT] -
          teclas[pygame.K_LEFT]) * 5
    x = max(30, min(570, x))
    if tiro:
        tiro.y -= 10
        if tiro.bottom < 0:
            tiro = None

    passo = lado * (1 + (32 - len(aliens)) // 8)
    if any(a.right + passo > 590 or a.left + passo < 10
           for a, _ in aliens):
        lado = -lado
        for a, _ in aliens:
            a.y += 12
    else:
        for a, _ in aliens:
            a.x += passo

    for par in aliens:
        if tiro and tiro.colliderect(par[0]):
            aliens.remove(par)
            boom = par[0].move(3, 0)
            boom_t = 12
            tiro = None
            pontos += 10
            break
    if not aliens:
        aliens = onda()
    if any(a.bottom > 345 for a, _ in aliens):
        aliens = onda()
        pontos = 0

    if random.random() < 0.03:
        a, _ = random.choice(aliens)
        bombas.append(pygame.Rect(a.centerx, a.bottom,
                                  4, 12))
    for b in bombas[:]:
        b.y += 5
        if b.colliderect((x - 19, 355, 39, 15)):
            bombas.remove(b)
            vidas -= 1
            choque = 30
        elif b.top > 400:
            bombas.remove(b)
    if vidas == 0:
        aliens = onda()
        pontos = 0
        vidas = 3

    tela.fill((8, 8, 20))
    for estrela in estrelas:
        pygame.draw.circle(tela, (110, 110, 150),
                           estrela, 1)
    for a, img in aliens:
        tela.blit(img, a)
    if boom_t:
        tela.blit(explosao, boom)
        boom_t -= 1
    if tiro:
        pygame.draw.rect(tela, "white", tiro)
    for b in bombas:
        pygame.draw.rect(tela, (255, 90, 90), b)
    if choque % 6 < 3:
        tela.blit(nave, (x - 19, 355))
    choque = max(0, choque - 1)
    placar = fonte.render(f"PONTOS {pontos}", 1, "white")
    tela.blit(placar, (14, 10))
    texto = fonte.render(f"VIDAS {vidas}", 1, "white")
    tela.blit(texto, (500, 10))
    pygame.display.flip()
    relogio.tick(60)

pygame.quit()
