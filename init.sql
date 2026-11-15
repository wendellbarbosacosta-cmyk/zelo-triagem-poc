CREATE TABLE IF NOT EXISTS regras_triagem (
    id SERIAL PRIMARY KEY,
    codigo_regra VARCHAR(10) UNIQUE NOT NULL,
    tipo_ocorrencia VARCHAR(150) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    urgencia_base VARCHAR(10) NOT NULL CHECK (urgencia_base IN ('Baixa', 'Média', 'Alta')),
    condicao_modificadora TEXT,
    responsavel VARCHAR(100) NOT NULL,
    is_sensivel BOOLEAN NOT NULL DEFAULT FALSE,
    sla_horas INT NOT NULL
);

INSERT INTO regras_triagem 
(codigo_regra, tipo_ocorrencia, categoria, urgencia_base, condicao_modificadora, responsavel, is_sensivel, sla_horas) 
VALUES
('1', 'Lâmpada queimada em área comum', 'Elétrica simples', 'Baixa', 'Escada ou garagem à noite: sobe', 'Zelador', FALSE, 72),
('2', 'Fio exposto, choque, faísca, tomada esquentando', 'Elétrica', 'Alta', NULL, 'Síndico (+ eletricista)', TRUE, 2),
('3b', 'Disjuntor desarmando', 'Elétrica', 'Média', 'Repetição ou cheiro de queimado: sobe', 'Síndico (+ eletricista)', TRUE, 24),
('4', 'Vazamento pequeno em área comum (torneira, cano pingando)', 'Hidráulica', 'Média', 'Água atingindo elétrica, elevador ou apartamento: sobe', 'Zelador', FALSE, 24),
('5', 'Cano estourado, alagamento', 'Hidráulica', 'Alta', NULL, 'Manutenção (encanador)', FALSE, 2),
('6', 'Falta de água / bomba parada', 'Hidráulica', 'Alta', 'Só 1 apartamento: desce', 'Manutenção', FALSE, 4),
('8', 'Trinca ou rachadura em parede, viga ou laje', 'Estrutura', 'Alta', NULL, 'Síndico (+ engenharia)', TRUE, 12),
('10', 'Cheiro de gás', 'Gás', 'Alta', NULL, 'Síndico (+ concessionária)', TRUE, 1),
('11', 'Elevador parado', 'Elevador', 'Alta', 'Pessoa presa: imediato', 'Síndico (+ empresa do elevador)', TRUE, 1),
('16', 'Portão da garagem travado ou sem fechar', 'Acesso', 'Média', 'À noite ou portão aberto: sobe', 'Manutenção', FALSE, 12),
('19', 'Barulho de vizinho', 'Convivência', 'Baixa', 'Depois das 22h ou repetição: sobe', 'Portaria', FALSE, 24),
('23', 'Piscina com água baixa ou suja', 'Lazer', 'Baixa', 'Férias ou temporada: sobe', 'Zelador', FALSE, 48),
('24', 'Ralo de sucção da piscina solto ou quebrado', 'Lazer / segurança', 'Alta', NULL, 'Síndico', TRUE, 2)
ON CONFLICT (codigo_regra) DO NOTHING;