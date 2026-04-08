import uuid
from datetime import datetime, timedelta

import pytest

from models.collection import Collection, Comment
from services.clean.base import SelectorBase
from services.clean.mean import MeanSelector
from services.clean.median import MedianSelector
from services.clean.mode import ModeSelector
from services.clean.percentile import PercentileSelector
from services.clean.service import build_dataset_name, group_by_user
from services.clean.short_comments import ShortCommentsSelector
from services.clean.stats import compute_central_measures, remove_outliers_iqr
from services.clean.time_interval import TimeIntervalSelector

# ---------------------------------------------------------------------------
# Helpers — Dummy comment factory
# ---------------------------------------------------------------------------


def _make_comments(
    users: dict[str, int],
    *,
    collection_id: uuid.UUID | None = None,
    text_factory=None,
    published_at_factory=None,
) -> list[Comment]:
    """Factory de Dummy comments: gera N comentários por user_id."""
    cid = collection_id or uuid.uuid4()
    comments = []
    for channel_id, count in users.items():
        for i in range(count):
            text = (
                text_factory(channel_id, i)
                if text_factory
                else f"comentário {i} do {channel_id}"
            )
            pub = (
                published_at_factory(channel_id, i)
                if published_at_factory
                else datetime(2024, 1, 1) + timedelta(minutes=i)
            )
            comments.append(
                Comment(
                    id=uuid.uuid4(),
                    collection_id=cid,
                    comment_id=f"{channel_id}_c{i}",
                    parent_id=None,
                    author_channel_id=channel_id,
                    author_display_name=f"User {channel_id}",
                    text_original=text,
                    text_display=text,
                    like_count=0,
                    reply_count=0,
                    published_at=pub,
                    updated_at=pub,
                )
            )
    return comments


# ---------------------------------------------------------------------------
# Testes unitários — funções puras
# ---------------------------------------------------------------------------


class TestGroupByUser:
    def test_agrupa_por_author_channel_id(self):
        comments = _make_comments({"A": 3, "B": 2})
        groups = group_by_user(comments)
        assert len(groups["A"]) == 3
        assert len(groups["B"]) == 2

    def test_fallback_para_display_name_sem_channel_id(self):
        c = Comment(
            id=uuid.uuid4(),
            collection_id=uuid.uuid4(),
            comment_id="x",
            author_channel_id=None,
            author_display_name="Anon",
            text_original="hi",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        groups = group_by_user([c])
        assert "Anon" in groups


class TestBuildDatasetName:
    def test_ordem_canonica(self):
        name = build_dataset_name("dQw4w9", ["intervalo", "percentil"])
        assert name == "dQw4w9_percentil_intervalo"

    def test_criterio_unico(self):
        assert build_dataset_name("abc", ["media"]) == "abc_media"

    def test_todos_criterios(self):
        all_criteria = [
            "perfil",
            "identicos",
            "curtos",
            "mediana",
            "moda",
            "media",
            "percentil",
            "intervalo",
        ]
        name = build_dataset_name("v1", all_criteria)
        assert (
            name == "v1_percentil_media_moda_mediana_curtos_intervalo_identicos_perfil"
        )


class TestRemoveOutliersIQR:
    def test_remove_outlier_extremo(self):
        values = [1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 100.0]
        clean = remove_outliers_iqr(values)
        assert 100.0 not in clean

    def test_retorna_intacto_se_menos_de_4_valores(self):
        values = [1.0, 2.0, 3.0]
        assert remove_outliers_iqr(values) == values

    def test_sem_outliers_retorna_tudo(self):
        values = [2.0, 3.0, 3.0, 4.0, 4.0, 5.0]
        clean = remove_outliers_iqr(values)
        assert len(clean) == len(values)


class TestComputeCentralMeasures:
    def test_medidas_com_distribuicao_conhecida(self):
        user_counts = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
        m = compute_central_measures(user_counts)
        assert m["mean"] > 0
        assert m["median"] > 0
        assert m["iqr_lower"] <= m["iqr_upper"]

    def test_vazio_retorna_zeros(self):
        m = compute_central_measures({})
        assert m["mean"] == 0.0


# ---------------------------------------------------------------------------
# Testes dos seletores (OCP — cada classe SelectorBase)
# ---------------------------------------------------------------------------


class TestPercentileSelector:
    def test_seleciona_top_30_por_volume(self):
        # 10 usuários: A=10, B=9, ..., J=1
        comments = _make_comments({chr(65 + i): 10 - i for i in range(10)})
        groups = group_by_user(comments)
        selector = PercentileSelector(top_percent=0.30)
        selected = selector.select(groups)

        # Top 30% de 10 = 3 usuários
        assert len(selected) == 3
        assert "A" in selected
        assert "B" in selected
        assert "C" in selected

    def test_vazio_retorna_vazio(self):
        assert PercentileSelector().select({}) == set()

    def test_implementa_selector_base(self):
        assert isinstance(PercentileSelector(), SelectorBase)


class TestMeanSelector:
    def test_outlier_nao_distorce_threshold(self):
        # Usuários com 1,1,1,1,1000 — outlier não deve inflar a média
        comments = _make_comments({"A": 1, "B": 1, "C": 1, "D": 1, "E": 1000})
        groups = group_by_user(comments)
        selected = MeanSelector().select(groups)

        # E (1000) está muito acima da média sem outlier (~1)
        assert "E" in selected

    def test_seleciona_acima_da_media(self):
        comments = _make_comments({"A": 5, "B": 3, "C": 1, "D": 1})
        groups = group_by_user(comments)
        selected = MeanSelector().select(groups)
        assert "A" in selected

    def test_implementa_selector_base(self):
        assert isinstance(MeanSelector(), SelectorBase)


class TestMedianSelector:
    def test_seleciona_acima_da_mediana(self):
        comments = _make_comments({"A": 10, "B": 5, "C": 2, "D": 1, "E": 1})
        groups = group_by_user(comments)
        selected = MedianSelector().select(groups)
        assert "A" in selected
        assert "B" in selected

    def test_implementa_selector_base(self):
        assert isinstance(MedianSelector(), SelectorBase)


class TestModeSelector:
    def test_seleciona_acima_da_moda(self):
        # Moda = 1 (maioria tem 1 comentário)
        comments = _make_comments({"A": 5, "B": 1, "C": 1, "D": 1, "E": 1})
        groups = group_by_user(comments)
        selected = ModeSelector().select(groups)
        assert "A" in selected

    def test_implementa_selector_base(self):
        assert isinstance(ModeSelector(), SelectorBase)


class TestShortCommentsSelector:
    def test_detecta_usuario_com_maioria_curtos(self):
        def text_fn(uid, i):
            if uid == "A":
                return "hi"  # 2 chars, abaixo de 20
            return f"este é um comentário mais longo número {i}"

        comments = _make_comments({"A": 5, "B": 5}, text_factory=text_fn)
        groups = group_by_user(comments)
        selected = ShortCommentsSelector(threshold_chars=20).select(groups)
        assert "A" in selected
        assert "B" not in selected

    def test_detecta_usuario_com_alta_repeticao(self):
        def text_fn(uid, i):
            if uid == "A":
                return "spam repetido exatamente igual"
            return f"comentário único número {i}"

        comments = _make_comments({"A": 5, "B": 5}, text_factory=text_fn)
        groups = group_by_user(comments)
        selected = ShortCommentsSelector(threshold_chars=5).select(groups)
        # A tem 100% repetição (>0.5), mas caracteres não são curtos
        # Taxa de repetição: 1 - 1/5 = 0.8 > 0.5
        assert "A" in selected

    def test_implementa_selector_base(self):
        assert isinstance(ShortCommentsSelector(), SelectorBase)


class TestTimeIntervalSelector:
    def test_detecta_rajada_dentro_do_threshold(self):
        def pub_fn(uid, i):
            if uid == "A":
                return datetime(2024, 1, 1, 12, 0, 0) + timedelta(seconds=5 * i)
            return datetime(2024, 1, 1, 12, 0, 0) + timedelta(hours=i)

        comments = _make_comments({"A": 3, "B": 3}, published_at_factory=pub_fn)
        groups = group_by_user(comments)
        selected = TimeIntervalSelector(threshold_seconds=30).select(groups)
        assert "A" in selected
        assert "B" not in selected

    def test_usuario_com_1_comentario_nao_selecionado(self):
        comments = _make_comments({"A": 1})
        groups = group_by_user(comments)
        selected = TimeIntervalSelector().select(groups)
        assert "A" not in selected

    def test_implementa_selector_base(self):
        assert isinstance(TimeIntervalSelector(), SelectorBase)


# ---------------------------------------------------------------------------
# Teste de interseção de critérios
# ---------------------------------------------------------------------------


class TestUniaoCriterios:
    def test_uniao_percentil_e_intervalo(self):
        """Usuários que atendem QUALQUER critério entram no dataset."""

        def pub_fn(uid, i):
            if uid in ("A", "B"):
                return datetime(2024, 1, 1, 12, 0, 0) + timedelta(seconds=5 * i)
            return datetime(2024, 1, 1, 12, 0, 0) + timedelta(hours=i)

        # 10 usuários → top 30% = 3 (A, B, C)
        # A e B postam em rajada, C não
        comments = _make_comments(
            {
                "A": 10,
                "B": 8,
                "C": 6,
                "D": 2,
                "E": 1,
                "F": 1,
                "G": 1,
                "H": 1,
                "I": 1,
                "J": 1,
            },
            published_at_factory=pub_fn,
        )
        groups = group_by_user(comments)

        pct = PercentileSelector(top_percent=0.30).select(groups)
        interval = TimeIntervalSelector(threshold_seconds=30).select(groups)
        union = pct | interval

        # A e B: top volume + rajada
        assert "A" in union
        assert "B" in union
        # C: top volume apenas — entra na união
        assert "C" in union
        # D: nem top volume nem rajada
        assert "D" not in union


# ---------------------------------------------------------------------------
# Testes de integração — endpoints HTTP
# ---------------------------------------------------------------------------


@pytest.fixture
def completed_collection(db, admin_user):
    """Cria coleta concluída com 5 usuários de volumes variados."""
    collection = Collection(
        video_id="dQw4w9WgXcQ",
        status="completed",
        total_comments=26,
        enrich_status="done",
        collected_by=admin_user.id,
    )
    db.add(collection)
    db.flush()

    users_data = {"A": 10, "B": 5, "C": 3, "D": 2, "E": 1}
    for channel_id, count in users_data.items():
        for i in range(count):
            db.add(
                Comment(
                    collection_id=collection.id,
                    comment_id=f"{channel_id}_c{i}",
                    author_channel_id=channel_id,
                    author_display_name=f"User {channel_id}",
                    text_original=f"comentário {i} do {channel_id}",
                    like_count=0,
                    reply_count=0,
                    published_at=datetime(2024, 1, 1, 0, i, 0),
                    updated_at=datetime(2024, 1, 1, 0, i, 0),
                )
            )
    db.commit()
    db.refresh(collection)
    return collection


class TestPreviewEndpoint:
    def test_preview_retorna_contagem_por_criterio(
        self, client, auth_as_user, completed_collection
    ):
        resp = client.get(
            "/clean/preview",
            params={
                "collection_id": str(completed_collection.id),
                "criteria": "percentil,media",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_users"] == 5
        assert "percentil" in data["by_criteria"]
        assert "media" in data["by_criteria"]
        assert data["central_measures"]["mean"] > 0

    def test_preview_sem_token_retorna_401(self, client, completed_collection):
        resp = client.get(
            "/clean/preview",
            params={
                "collection_id": str(completed_collection.id),
                "criteria": "percentil",
            },
        )
        assert resp.status_code == 401

    def test_preview_coleta_nao_concluida_retorna_409(
        self, client, db, auth_as_user, admin_user
    ):
        running = Collection(
            video_id="abc",
            status="running",
            collected_by=admin_user.id,
        )
        db.add(running)
        db.commit()
        db.refresh(running)

        resp = client.get(
            "/clean/preview",
            params={
                "collection_id": str(running.id),
                "criteria": "percentil",
            },
        )
        assert resp.status_code == 409

    def test_preview_coleta_inexistente_retorna_404(self, client, auth_as_user):
        resp = client.get(
            "/clean/preview",
            params={
                "collection_id": str(uuid.uuid4()),
                "criteria": "percentil",
            },
        )
        assert resp.status_code == 404


class TestCreateDatasetEndpoint:
    def test_cria_dataset_com_sucesso(self, client, auth_as_user, completed_collection):
        resp = client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["percentil"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "dQw4w9WgXcQ_percentil"
        assert data["total_users_selected"] > 0
        assert data["video_id"] == "dQw4w9WgXcQ"

    def test_dataset_duplicado_retorna_409(
        self, client, auth_as_user, completed_collection
    ):
        client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["percentil"],
            },
        )
        resp = client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["percentil"],
            },
        )
        assert resp.status_code == 409

    def test_sem_criterio_retorna_422(self, client, auth_as_user, completed_collection):
        resp = client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": [],
            },
        )
        assert resp.status_code == 422

    def test_coleta_nao_concluida_retorna_409(
        self, client, db, auth_as_user, admin_user
    ):
        running = Collection(
            video_id="abc",
            status="running",
            collected_by=admin_user.id,
        )
        db.add(running)
        db.commit()
        db.refresh(running)

        resp = client.post(
            "/clean",
            json={
                "collection_id": str(running.id),
                "criteria": ["percentil"],
            },
        )
        assert resp.status_code == 409

    def test_perfil_usa_dados_da_coleta(
        self, client, auth_as_user, completed_collection
    ):
        """Critério perfil funciona sem API key — usa dados já coletados."""
        resp = client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["perfil"],
            },
        )
        # Pode ser 201 (se encontrou suspeitos) ou 422 (se nenhum selecionado)
        assert resp.status_code in (201, 422)

    def test_sem_token_retorna_401(self, client, completed_collection):
        resp = client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["percentil"],
            },
        )
        assert resp.status_code == 401


class TestListDatasetsEndpoint:
    def test_lista_datasets(self, client, auth_as_user, completed_collection):
        # Criar um dataset primeiro
        client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["percentil"],
            },
        )
        resp = client.get("/clean/datasets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["name"] == "dQw4w9WgXcQ_percentil"

    def test_lista_filtrada_por_video_id(
        self, client, auth_as_user, completed_collection
    ):
        client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["percentil"],
            },
        )
        resp = client.get(
            "/clean/datasets",
            params={"video_id": "dQw4w9WgXcQ"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        resp2 = client.get(
            "/clean/datasets",
            params={"video_id": "INEXISTENTE"},
        )
        assert resp2.status_code == 200
        assert len(resp2.json()) == 0


class TestDownloadDatasetEndpoint:
    def test_download_json(self, client, auth_as_user, completed_collection):
        create_resp = client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["percentil"],
            },
        )
        dataset_id = create_resp.json()["dataset_id"]

        resp = client.get(
            f"/clean/datasets/{dataset_id}/download",
            params={"format": "json"},
        )
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        data = resp.json()
        assert "dataset" in data
        assert "users" in data
        assert "comments" in data

    def test_download_csv(self, client, auth_as_user, completed_collection):
        create_resp = client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["percentil"],
            },
        )
        dataset_id = create_resp.json()["dataset_id"]

        resp = client.get(
            f"/clean/datasets/{dataset_id}/download",
            params={"format": "csv"},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_download_dataset_inexistente_retorna_404(self, client, auth_as_user):
        resp = client.get(
            f"/clean/datasets/{uuid.uuid4()}/download",
            params={"format": "json"},
        )
        assert resp.status_code == 404


class TestDeleteDatasetEndpoint:
    def test_deleta_dataset(self, client, auth_as_user, completed_collection):
        create_resp = client.post(
            "/clean",
            json={
                "collection_id": str(completed_collection.id),
                "criteria": ["percentil"],
            },
        )
        dataset_id = create_resp.json()["dataset_id"]

        resp = client.delete(f"/clean/datasets/{dataset_id}")
        assert resp.status_code == 204

        # Confirmar que foi deletado
        resp2 = client.get(
            f"/clean/datasets/{dataset_id}/download",
            params={"format": "json"},
        )
        assert resp2.status_code == 404

    def test_deleta_dataset_inexistente_retorna_404(self, client, auth_as_user):
        resp = client.delete(f"/clean/datasets/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Testes unitários adicionais — cobertura 100%
# ---------------------------------------------------------------------------


class TestIdenticalSelector:
    def test_constructor_e_select_vazio(self, db):
        """IdenticalSelector com user_comments vazio retorna set vazio."""
        from services.clean.identical import IdenticalSelector

        selector = IdenticalSelector(db=db, collection_id=str(uuid.uuid4()))
        assert selector.select({}) == set()

    def test_select_detecta_texto_identico_em_outra_coleta(self, db, admin_user):
        """Detecta texto duplicado entre coletas diferentes."""
        from services.clean.identical import IdenticalSelector

        # Coleta 1
        col1 = Collection(
            video_id="vid_A",
            status="completed",
            collected_by=admin_user.id,
            total_comments=1,
        )
        db.add(col1)
        db.flush()

        c1 = Comment(
            collection_id=col1.id,
            comment_id="c1",
            author_channel_id="UC_dup",
            author_display_name="Dup",
            text_original="texto repetido",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        db.add(c1)
        db.flush()

        # Coleta 2
        col2 = Collection(
            video_id="vid_B",
            status="completed",
            collected_by=admin_user.id,
            total_comments=1,
        )
        db.add(col2)
        db.flush()

        c2 = Comment(
            collection_id=col2.id,
            comment_id="c2",
            author_channel_id="UC_dup",
            author_display_name="Dup",
            text_original="texto repetido",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 1, 2),
            updated_at=datetime(2024, 1, 2),
        )
        db.add(c2)
        db.commit()

        user_comments = {"UC_dup": [c1]}
        selector = IdenticalSelector(db=db, collection_id=str(col1.id))
        selected = selector.select(user_comments)
        assert "UC_dup" in selected

    def test_select_sem_match_em_outras_coletas(self, db, admin_user):
        """Sem texto repetido em outra coleta, ninguem selecionado."""
        from services.clean.identical import IdenticalSelector

        col = Collection(
            video_id="vid_solo",
            status="completed",
            collected_by=admin_user.id,
            total_comments=1,
        )
        db.add(col)
        db.flush()

        c = Comment(
            collection_id=col.id,
            comment_id="c_solo",
            author_channel_id="UC_solo",
            author_display_name="Solo",
            text_original="texto unico",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        db.add(c)
        db.commit()

        user_comments = {"UC_solo": [c]}
        selector = IdenticalSelector(db=db, collection_id=str(col.id))
        selected = selector.select(user_comments)
        assert selected == set()


class TestProfileSelectorEdgeCases:
    def test_empty_input_retorna_vazio(self):
        """ProfileSelector com input vazio retorna set vazio."""
        from services.clean.profile import ProfileSelector

        assert ProfileSelector().select({}) == set()

    def test_naive_timezone_handling(self):
        """Datetime naive recebe UTC antes de comparar."""
        from services.clean.profile import ProfileSelector

        c = Comment(
            id=uuid.uuid4(),
            collection_id=uuid.uuid4(),
            comment_id="tz_test",
            author_channel_id="UC_tz",
            author_display_name="TZ",
            text_original="hi",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
            # Canal criado ontem — naive datetime
            author_channel_published_at=datetime(2024, 1, 1),
            author_profile_image_url="https://normal.com/pic.jpg",
        )
        user_comments = {"UC_tz": [c]}
        # Canal antigo, nao recente — nao deve ser selecionado
        selected = ProfileSelector().select(user_comments)
        assert "UC_tz" not in selected

    def test_or_logic_default_avatar_ou_canal_recente(self):
        """Basta avatar padrao OU canal recente para selecionar."""
        from datetime import UTC

        from services.clean.profile import ProfileSelector

        # Apenas avatar padrao
        c1 = Comment(
            id=uuid.uuid4(),
            collection_id=uuid.uuid4(),
            comment_id="avatar_test",
            author_channel_id="UC_avatar",
            author_display_name="Avatar",
            text_original="hi",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
            author_profile_image_url=("https://yt4.ggpht.com/a/default-user=s48"),
            author_channel_published_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        user_comments = {"UC_avatar": [c1]}
        selected = ProfileSelector().select(user_comments)
        assert "UC_avatar" in selected


class TestShortCommentsSelectorEmpty:
    def test_empty_comments_list_skip(self):
        """Usuarios com lista vazia de comentarios sao ignorados."""
        selector = ShortCommentsSelector(threshold_chars=20)
        user_comments = {"UC_empty": []}
        selected = selector.select(user_comments)
        assert "UC_empty" not in selected


class TestCentralMeasureSelectorEmpty:
    def test_user_counts_vazio_retorna_vazio(self):
        """CentralMeasureSelector com input vazio retorna set vazio."""
        selector = MeanSelector()
        assert selector.select({}) == set()


class TestComputeCentralMeasuresSmallSample:
    def test_q1_q3_com_menos_de_4_valores(self):
        """Com <4 valores, Q1=min e Q3=max."""
        m = compute_central_measures({"A": 5, "B": 10})
        assert m["iqr_lower"] == 5.0
        assert m["iqr_upper"] == 10.0


class TestGroupByUserExcludeChannel:
    def test_exclui_video_channel_id(self):
        """Comentarios do dono do canal sao excluidos."""
        comments = _make_comments({"OWNER": 5, "A": 3})
        groups = group_by_user(comments, exclude_channel_id="OWNER")
        assert "OWNER" not in groups
        assert "A" in groups


class TestBuildSelectorAllCases:
    def test_all_selectors_and_unknown(self, db):
        """Testa todos os cases do _build_selector."""
        from services.clean.service import _build_selector

        s = _build_selector(
            "percentil",
            threshold_chars=20,
            threshold_seconds=30,
        )
        assert isinstance(s, PercentileSelector)

        s = _build_selector(
            "media",
            threshold_chars=20,
            threshold_seconds=30,
        )
        assert isinstance(s, MeanSelector)

        s = _build_selector(
            "moda",
            threshold_chars=20,
            threshold_seconds=30,
        )
        from services.clean.mode import ModeSelector as MS

        assert isinstance(s, MS)

        s = _build_selector(
            "mediana",
            threshold_chars=20,
            threshold_seconds=30,
        )
        assert isinstance(s, MedianSelector)

        s = _build_selector(
            "curtos",
            threshold_chars=42,
            threshold_seconds=30,
        )
        assert isinstance(s, ShortCommentsSelector)
        assert s.threshold_chars == 42

        s = _build_selector(
            "intervalo",
            threshold_chars=20,
            threshold_seconds=99,
        )
        assert isinstance(s, TimeIntervalSelector)
        assert s.threshold_seconds == 99

        from services.clean.identical import IdenticalSelector

        s = _build_selector(
            "identicos",
            threshold_chars=20,
            threshold_seconds=30,
            db=db,
            collection_id=uuid.uuid4(),
        )
        assert isinstance(s, IdenticalSelector)

        from services.clean.profile import ProfileSelector

        s = _build_selector(
            "perfil",
            threshold_chars=20,
            threshold_seconds=30,
        )
        assert isinstance(s, ProfileSelector)

        with pytest.raises(ValueError, match="desconhecido"):
            _build_selector(
                "invalido",
                threshold_chars=20,
                threshold_seconds=30,
            )


class TestPreviewThresholdOutputs:
    def test_preview_curtos_inclui_threshold_chars(
        self, client, auth_as_user, completed_collection
    ):
        """Preview com criterio 'curtos' inclui threshold_chars."""
        resp = client.get(
            "/clean/preview",
            params={
                "collection_id": str(completed_collection.id),
                "criteria": "curtos",
                "threshold_chars": 50,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        entry = data["by_criteria"]["curtos"]
        assert entry["threshold_chars"] == 50

    def test_preview_intervalo_inclui_threshold_seconds(
        self, client, auth_as_user, completed_collection
    ):
        """Preview com criterio 'intervalo' inclui threshold_seconds."""
        resp = client.get(
            "/clean/preview",
            params={
                "collection_id": str(completed_collection.id),
                "criteria": "intervalo",
                "threshold_seconds": 120,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        entry = data["by_criteria"]["intervalo"]
        assert entry["threshold_seconds"] == 120


# ---------------------------------------------------------------------------
# Testes de integração — Import de dataset
# ---------------------------------------------------------------------------


class TestImportDatasetEndpoint:
    def test_import_dataset_valido(self, client, auth_as_user, completed_collection):
        """Import de dataset com video_id valido cria dataset."""
        resp = client.post(
            "/clean/import",
            json={
                "dataset": {
                    "name": "imported_ds",
                    "video_id": "dQw4w9WgXcQ",
                    "criteria_applied": ["percentil"],
                },
                "users": [
                    {
                        "author_channel_id": "A",
                        "author_display_name": "User A",
                        "comment_count": 10,
                        "matched_criteria": ["percentil"],
                    },
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "imported_ds"
        assert data["total_users_selected"] == 1

    def test_import_dataset_video_id_inexistente_404(self, client, auth_as_user):
        """Import com video_id sem coleta concluida retorna 404."""
        resp = client.post(
            "/clean/import",
            json={
                "dataset": {
                    "name": "ds_fail",
                    "video_id": "INEXISTENTE",
                    "criteria_applied": ["media"],
                },
                "users": [
                    {
                        "author_channel_id": "X",
                        "comment_count": 1,
                    },
                ],
            },
        )
        assert resp.status_code == 404

    def test_import_dataset_coleta_nao_concluida_404(
        self, client, db, auth_as_user, admin_user
    ):
        """Import com coleta nao concluida retorna 404."""
        running = Collection(
            video_id="running_vid",
            status="running",
            collected_by=admin_user.id,
        )
        db.add(running)
        db.commit()

        resp = client.post(
            "/clean/import",
            json={
                "dataset": {
                    "name": "ds_running",
                    "video_id": "running_vid",
                    "criteria_applied": [],
                },
                "users": [
                    {
                        "author_channel_id": "X",
                        "comment_count": 1,
                    },
                ],
            },
        )
        assert resp.status_code == 404

    def test_import_dataset_nome_duplicado_409(
        self, client, auth_as_user, completed_collection
    ):
        """Import com nome de dataset ja existente retorna 409."""
        client.post(
            "/clean/import",
            json={
                "dataset": {
                    "name": "dup_name",
                    "video_id": "dQw4w9WgXcQ",
                    "criteria_applied": [],
                },
                "users": [
                    {
                        "author_channel_id": "A",
                        "comment_count": 1,
                    },
                ],
            },
        )
        resp = client.post(
            "/clean/import",
            json={
                "dataset": {
                    "name": "dup_name",
                    "video_id": "dQw4w9WgXcQ",
                    "criteria_applied": [],
                },
                "users": [
                    {
                        "author_channel_id": "B",
                        "comment_count": 1,
                    },
                ],
            },
        )
        assert resp.status_code == 409


class TestImportDatasetChunkEndpoint:
    def test_import_chunk_adiciona_usuarios(
        self, client, auth_as_user, completed_collection
    ):
        """Import-chunk adiciona usuarios a dataset existente."""
        # Criar dataset via import
        create_resp = client.post(
            "/clean/import",
            json={
                "dataset": {
                    "name": "chunk_ds",
                    "video_id": "dQw4w9WgXcQ",
                    "criteria_applied": ["media"],
                },
                "users": [
                    {
                        "author_channel_id": "A",
                        "comment_count": 5,
                    },
                ],
            },
        )
        ds_id = create_resp.json()["dataset_id"]

        resp = client.post(
            "/clean/import-chunk",
            json={
                "dataset_id": ds_id,
                "users": [
                    {
                        "author_channel_id": "B",
                        "author_display_name": "User B",
                        "comment_count": 3,
                        "matched_criteria": ["media"],
                    },
                ],
                "done": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_users"] == 2
        assert data["chunk_received"] == 1
        assert data["done"] is True

    def test_import_chunk_dataset_inexistente_404(self, client, auth_as_user):
        """Import-chunk com dataset_id inexistente retorna 404."""
        resp = client.post(
            "/clean/import-chunk",
            json={
                "dataset_id": str(uuid.uuid4()),
                "users": [
                    {
                        "author_channel_id": "X",
                        "comment_count": 1,
                    },
                ],
                "done": False,
            },
        )
        assert resp.status_code == 404


# -------------------------------------------------------------------
# Cobertura adicional — identical.py branch not texts
# -------------------------------------------------------------------


class TestIdenticalSelectorEmptyTexts:
    def test_user_with_empty_comment_list_skipped(self, db, admin_user):
        """Usuario com lista de comentarios vazia e ignorado."""
        from services.clean.identical import IdenticalSelector

        col = Collection(
            video_id="vid_empty_txt",
            status="completed",
            collected_by=admin_user.id,
            total_comments=0,
        )
        db.add(col)
        db.commit()

        # Lista vazia de comments gera texts vazio
        user_comments: dict[str, list[Comment]] = {"UC_empty_txt": []}
        selector = IdenticalSelector(db=db, collection_id=str(col.id))
        selected = selector.select(user_comments)
        assert "UC_empty_txt" not in selected
