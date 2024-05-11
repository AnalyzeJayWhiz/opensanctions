import shutil
from zavod import settings
from zavod.meta import Dataset
from zavod.archive import STATISTICS_FILE, INDEX_FILE, STATEMENTS_FILE
from zavod.archive import get_dataset_resource, clear_data_path
from zavod.archive import iter_dataset_statements, iter_previous_statements
from zavod.crawl import crawl_dataset
from zavod.store import get_view, clear_store
from zavod.exporters import export_dataset
from zavod.publish import publish_dataset, publish_failure
from zavod.exc import RunFailedException


def test_publish_dataset(testdataset1: Dataset):
    arch_path = settings.ARCHIVE_PATH / "datasets"
    release_path = arch_path / settings.RELEASE / testdataset1.name
    latest_path = arch_path / "latest" / testdataset1.name
    assert not release_path.joinpath(INDEX_FILE).exists()
    assert not latest_path.joinpath(INDEX_FILE).exists()
    clear_store(testdataset1)
    crawl_dataset(testdataset1)
    view = get_view(testdataset1)
    export_dataset(testdataset1, view)

    publish_dataset(testdataset1, latest=False)

    assert release_path.joinpath(INDEX_FILE).exists()
    assert not latest_path.joinpath(INDEX_FILE).exists()
    assert release_path.joinpath(STATEMENTS_FILE).exists()
    assert release_path.joinpath(STATISTICS_FILE).exists()
    assert release_path.joinpath("entities.ftm.json").exists()

    publish_dataset(testdataset1, latest=True)
    assert latest_path.joinpath(INDEX_FILE).exists()

    # Test backfill:
    clear_data_path(testdataset1.name)
    assert len(list(iter_dataset_statements(testdataset1))) > 5
    assert len(list(iter_previous_statements(testdataset1))) > 5
    path = get_dataset_resource(testdataset1, INDEX_FILE, backfill=False)
    assert not path.exists()
    path = get_dataset_resource(testdataset1, INDEX_FILE, backfill=True)
    assert path.exists()

    shutil.rmtree(latest_path)
    shutil.rmtree(release_path)


def test_publish_failure(testdataset1: Dataset):
    arch_path = settings.ARCHIVE_PATH / "datasets"
    latest_path = arch_path / "latest" / testdataset1.name
    assert testdataset1.data is not None
    testdataset1.data.format = "FAIL"
    try:
        crawl_dataset(testdataset1)
    except RunFailedException:
        publish_failure(testdataset1, latest=True)
    clear_data_path(testdataset1.name)

    assert not latest_path.joinpath("statements.pack").exists()
    assert latest_path.joinpath("index.json").exists()
    assert latest_path.joinpath("issues.json").exists()
    shutil.rmtree(latest_path)
