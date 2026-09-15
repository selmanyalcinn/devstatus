from devstatus.models import Artifact
from devstatus.resolvers.classifier import classify, extract_version, catalog


def test_extract_version():
    assert extract_version('git version 2.43.0') == '2.43.0'
    assert extract_version('go version go1.24.3 linux/amd64') == '1.24.3'
    assert extract_version('Cool Runtime v2.7.4-beta1') == '2.7.4-beta1'


def test_catalog_is_large_and_unique():
    rules=catalog(); ids=[r['id'] for r in rules]
    assert len(rules) >= 300
    assert len(ids) == len(set(ids))


def test_redis_merge():
    artifacts=[
        Artifact('apt:redis-server','redis-server','package','apt','8.2.1'),
        Artifact('apt:redis-tools','redis-tools','package','apt','8.2.1'),
        Artifact('service:redis-server.service','redis-server.service','service','systemd',status='running'),
    ]
    tools,_=classify(artifacts,set())
    redis=next(t for t in tools if t.id=='redis')
    assert redis.name=='Redis'
    assert redis.category[:2]==('Databases','Cache & Key-Value')
    assert redis.status=='running'
    assert len(redis.components) >= 2


def test_unknown_user_binary_is_visible_on_baseline():
    a=Artifact('bin:/home/me/.local/bin/coolx','coolx','binary','binary','1.2.3',path='/home/me/.local/bin/coolx')
    tools,_=classify([a],None)
    assert any(t.id.startswith('unclassified:') for t in tools)


def test_unknown_apt_baseline_is_hidden():
    a=Artifact('apt:random-os-package','random-os-package','package','apt','1.0',description='miscellaneous package')
    tools,_=classify([a],None)
    assert not any(t.id.startswith('unclassified:') for t in tools)


def test_unknown_new_apt_is_visible():
    a=Artifact('apt:totally-new-devtool','totally-new-devtool','package','apt','1.2.3',description='miscellaneous package')
    tools,_=classify([a],set())
    assert any(t.id.startswith('unclassified:') for t in tools)


def test_generic_classification_from_description_even_on_baseline():
    a=Artifact('apt:supermq','supermq','package','apt','1.0',description='high performance MQTT broker and event streaming platform')
    tools,_=classify([a],None)
    assert any(t.category[0]=='Messaging & Streaming' for t in tools)


def test_nvidia_structured_detection():
    arts=[Artifact('gpu:nvidia:0','NVIDIA GeForce RTX 3050','gpu','nvidia','595.84',metadata={'driver':'595.84'}),
          Artifact('nvidia:cuda-capability','NVIDIA CUDA driver capability','capability','nvidia','13.2')]
    tools,_=classify(arts,None)
    gpu=next(t for t in tools if t.id.startswith('hardware:'))
    assert gpu.version == 'driver 595.84'
    assert any(t.id=='nvidia-cuda-driver-capability' and t.version=='13.2' for t in tools)
