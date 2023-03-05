import uuid
from enum import Enum
from typing import List, Optional, cast

from pydantic import root_validator, validator

from hera.workflows.models import (
    AWSElasticBlockStoreVolumeSource as _ModelAWSElasticBlockStoreVolumeSource,
)
from hera.workflows.models import AzureDiskVolumeSource as _ModelAzureDiskVolumeSource
from hera.workflows.models import AzureFileVolumeSource as _ModelAzureFileVolumeSource
from hera.workflows.models import CephFSVolumeSource as _ModelCephFSVolumeSource
from hera.workflows.models import CinderVolumeSource as _ModelCinderVolumeSource
from hera.workflows.models import ConfigMapVolumeSource as _ModelConfigMapVolumeSource
from hera.workflows.models import CSIVolumeSource as _ModelCSIVolumeSource
from hera.workflows.models import (
    DownwardAPIVolumeSource as _ModelDownwardAPIVolumeSource,
)
from hera.workflows.models import EmptyDirVolumeSource as _ModelEmptyDirVolumeSource
from hera.workflows.models import EphemeralVolumeSource as _ModelEphemeralVolumeSource
from hera.workflows.models import FCVolumeSource as _ModelFCVolumeSource
from hera.workflows.models import FlexVolumeSource as _ModelFlexVolumeSource
from hera.workflows.models import FlockerVolumeSource as _ModelFlockerVolumeSource
from hera.workflows.models import (
    GCEPersistentDiskVolumeSource as _ModelGCEPersistentDiskVolumeSource,
)
from hera.workflows.models import GitRepoVolumeSource as _ModelGitRepoVolumeSource
from hera.workflows.models import GlusterfsVolumeSource as _ModelGlusterfsVolumeSource
from hera.workflows.models import HostPathVolumeSource as _ModelHostPathVolumeSource
from hera.workflows.models import ISCSIVolumeSource as _ModelISCSIVolumeSource
from hera.workflows.models import NFSVolumeSource as _ModelNFSVolumeSource
from hera.workflows.models import ObjectMeta
from hera.workflows.models import (
    PersistentVolumeClaimSpec as _ModelPersistentVolumeClaimSpec,
)
from hera.workflows.models import (
    PersistentVolumeClaimTemplate as _ModelPersistentVolumeClaimTemplate,
)
from hera.workflows.models import (
    PersistentVolumeClaimVolumeSource as _ModelPersistentVolumeClaimVolumeSource,
)
from hera.workflows.models import (
    PhotonPersistentDiskVolumeSource as _ModelPhotonPersistentDiskVolumeSource,
)
from hera.workflows.models import PortworxVolumeSource as _ModelPortworxVolumeSource
from hera.workflows.models import ProjectedVolumeSource as _ModelProjectedVolumeSource
from hera.workflows.models import QuobyteVolumeSource as _ModelQuobyteVolumeSource
from hera.workflows.models import RBDVolumeSource as _ModelRBDVolumeSource
from hera.workflows.models import ResourceRequirements
from hera.workflows.models import ScaleIOVolumeSource as _ModelScaleIOVolumeSource
from hera.workflows.models import SecretVolumeSource as _ModelSecretVolumeSource
from hera.workflows.models import StorageOSVolumeSource as _ModelStorageOSVolumeSource
from hera.workflows.models import Volume as _ModelVolume
from hera.workflows.models import VolumeMount as _ModelVolumeMount
from hera.workflows.models import (
    VsphereVirtualDiskVolumeSource as _ModelVsphereVirtualDiskVolumeSource,
)
from hera.workflows.validators import validate_storage_units


class AccessMode(Enum):
    """A representations of the volume access modes for Kubernetes.

    Notes
    -----
    See: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes for more information.
    """

    read_write_once = "ReadWriteOnce"
    """
    The volume can be mounted as read-write by a single node. ReadWriteOnce access mode still can allow multiple
    pods to access the volume when the pods are running on the same node
    """

    read_only_many = "ReadOnlyMany"
    """The volume can be mounted as read-only by many nodes"""

    read_write_many = "ReadWriteMany"
    """The volume can be mounted as read-write by many nodes"""

    read_write_once_pod = "ReadWriteOncePod"
    """
    The volume can be mounted as read-write by a single Pod. Use ReadWriteOncePod access mode if you want to
    ensure that only one pod across whole cluster can read that PVC or write to it. This is only supported for CSI
    volumes and Kubernetes version 1.22+.
    """

    def __str__(self):
        return str(self.value)


class _BaseVolume(_ModelVolumeMount):
    name: Optional[str] = None  # type: ignore

    @validator("name", pre=True)
    def _check_name(cls, v):
        if v is None:
            return str(uuid.uuid4())
        return v

    def _build_persistent_volume_claim_template(self) -> _ModelPersistentVolumeClaimTemplate:
        raise NotImplementedError

    def _build_volume(self) -> _ModelVolume:
        raise NotImplementedError

    def _build_volume_mount(self) -> _ModelVolumeMount:
        return _ModelVolumeMount(
            name=self.name,
            mount_path=self.mount_path,
            mount_propagation=self.mount_propagation,
            read_only=self.read_only,
            sub_path=self.sub_path,
            sub_path_expr=self.sub_path_expr,
        )


class AWSElasticBlockStoreVolumeVolume(_BaseVolume, _ModelAWSElasticBlockStoreVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            aws_elastic_block_store=_ModelAWSElasticBlockStoreVolumeSource(
                fs_type=self.fs_type, partition=self.partition, read_only=self.read_only, volume_id=self.volume_id
            ),
        )


class AzureDiskVolumeVolume(_BaseVolume, _ModelAzureDiskVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            azure_disk=_ModelAzureDiskVolumeSource(
                caching_mode=self.caching_mode,
                disk_name=self.disk_name,
                disk_uri=self.disk_uri,
                fs_type=self.fs_type,
                kind=self.kind,
                read_only=self.read_only,
            ),
        )


class AzureFileVolumeVolume(_BaseVolume, _ModelAzureFileVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            azure_file=_ModelAzureFileVolumeSource(
                read_only=self.read_only, secret_name=self.secret_name, share_name=self.share_name
            ),
        )


class CephFSVolumeVolume(_BaseVolume, _ModelCephFSVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            cephfs=_ModelCephFSVolumeSource(
                monitors=self.monitors,
                path=self.path,
                read_only=self.read_only,
                secret_file=self.secret_file,
                secret_ref=self.secret_ref,
                user=self.user,
            ),
        )


class CinderVolume(_BaseVolume, _ModelCinderVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            cinder=_ModelCinderVolumeSource(
                fs_type=self.fs_type,
                read_only=self.read_only,
                secret_ref=self.secret_ref,
                volume_id=self.volume_id,
            ),
        )


class ConfigMapVolume(_BaseVolume, _ModelConfigMapVolumeSource):  # type: ignore
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            config_map=_ModelConfigMapVolumeSource(
                default_mode=self.default_mode, items=self.items, name=self.name, optional=self.optional
            ),
        )


class CSIVolume(_BaseVolume, _ModelCSIVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            csi=_ModelCSIVolumeSource(
                driver=self.driver,
                fs_type=self.fs_type,
                node_publish_secret_ref=self.node_publish_secret_ref,
                read_only=self.read_only,
                volume_attributes=self.volume_attributes,
            ),
        )


class DownwardAPIVolume(_BaseVolume, _ModelDownwardAPIVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            downward_api=_ModelDownwardAPIVolumeSource(default_mode=self.default_mode, items=self.items),
        )


class EmptyDirVolume(_BaseVolume, _ModelEmptyDirVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name, empty_dir=_ModelEmptyDirVolumeSource(medium=self.medium, size_limit=self.size_limit)
        )


class EphemeralVolume(_BaseVolume, _ModelEphemeralVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name, ephemeral=_ModelEphemeralVolumeSource(volume_claim_template=self.volume_claim_template)
        )


class FCVolume(_BaseVolume, _ModelFCVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            fc=_ModelFCVolumeSource(
                fs_type=self.fs_type,
                lun=self.lun,
                read_only=self.read_only,
                target_ww_ns=self.target_ww_ns,
                wwids=self.wwids,
            ),
        )


class FlexVolume(_BaseVolume, _ModelFlexVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            flex_volume=_ModelFlexVolumeSource(
                driver=self.driver,
                fs_type=self.fs_type,
                options=self.options,
                read_only=self.read_only,
                secret_ref=self.secret_ref,
            ),
        )


class FlockerVolume(_BaseVolume, _ModelFlockerVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            flocker=_ModelFlockerVolumeSource(dataset_name=self.dataset_name, dataset_uuid=self.dataset_uuid),
        )


class GCEPersistentDiskVolume(_BaseVolume, _ModelGCEPersistentDiskVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            gce_persistent_disk=_ModelGCEPersistentDiskVolumeSource(
                fs_type=self.fs_type, partition=self.partition, pd_name=self.pd_name, read_only=self.read_only
            ),
        )


class GitRepoVolume(_BaseVolume, _ModelGitRepoVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            git_repo=_ModelGitRepoVolumeSource(
                directory=self.directory, repository=self.repository, revision=self.revision
            ),
        )


class GlusterfsVolume(_BaseVolume, _ModelGlusterfsVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            glusterfs=_ModelGlusterfsVolumeSource(endpoints=self.endpoints, path=self.path, read_only=self.read_only),
        )


class HostPathVolume(_BaseVolume, _ModelHostPathVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(name=self.name, host_path=_ModelHostPathVolumeSource(path=self.path, type=self.type))


class ISCSIVolume(_BaseVolume, _ModelISCSIVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            iscsi=_ModelISCSIVolumeSource(
                chap_auth_discovery=self.chap_auth_discovery,
                chap_auth_session=self.chap_auth_discovery,
                fs_type=self.fs_type,
                initiator_name=self.initiator_name,
                iqn=self.iqn,
                iscsi_interface=self.iscsi_interface,
                lun=self.lun,
                portals=self.portals,
                read_only=self.read_only,
                secret_ref=self.secret_ref,
                target_portal=self.target_portal,
            ),
        )


class NFSVolume(_BaseVolume, _ModelNFSVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(name=self.name, nfs=_ModelNFSVolumeSource(path=self.path, read_only=self.read_only))


class PhotonPersistentDiskVolume(_BaseVolume, _ModelPhotonPersistentDiskVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            photon_persistent_disk=_ModelPhotonPersistentDiskVolumeSource(fs_type=self.fs_type, pd_id=self.pd_id),
        )


class PortworxVolume(_BaseVolume, _ModelPortworxVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            portworx_volume=_ModelPortworxVolumeSource(
                fs_type=self.fs_type, read_only=self.read_only, volume_id=self.volume_id
            ),
        )


class ProjectedVolume(_BaseVolume, _ModelProjectedVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name, projected=_ModelProjectedVolumeSource(default_mode=self.default_mode, sources=self.sources)
        )


class QuobyteVolume(_BaseVolume, _ModelQuobyteVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            quobyte=_ModelQuobyteVolumeSource(
                group=self.group,
                read_only=self.read_only,
                registry=self.registry,
                tenant=self.tenant,
                user=self.user,
                volume=self.volume,
            ),
        )


class RBDVolume(_BaseVolume, _ModelRBDVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            rbd=_ModelRBDVolumeSource(
                fs_type=self.fs_type,
                image=self.image,
                keyring=self.keyring,
                monitors=self.monitors,
                pool=self.pool,
                read_only=self.read_only,
                secret_ref=self.secret_ref,
                user=self.user,
            ),
        )


class ScaleIOVolume(_BaseVolume, _ModelScaleIOVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            scale_io=_ModelScaleIOVolumeSource(
                fs_type=self.fs_type,
                gateway=self.gateway,
                protection_domain=self.protection_domain,
                read_only=self.read_only,
                secret_ref=self.secret_ref,
                ssl_enabled=self.ssl_enabled,
                storage_mode=self.storage_mode,
                storage_pool=self.storage_pool,
                system=self.system,
                volume_name=self.volume_name,
            ),
        )


class SecretVolume(_BaseVolume, _ModelSecretVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            secret=_ModelSecretVolumeSource(
                default_mode=self.default_mode, items=self.items, optional=self.optional, secret_name=self.secret_name
            ),
        )


class StorageOSVolume(_BaseVolume, _ModelStorageOSVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            storageos=_ModelStorageOSVolumeSource(
                fs_type=self.fs_type,
                read_only=self.read_only,
                secret_ref=self.secret_ref,
                volume_name=self.volume_name,
                volume_namespace=self.volume_namespace,
            ),
        )


class VsphereVirtualDiskVolume(_BaseVolume, _ModelVsphereVirtualDiskVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            vsphere_volume=_ModelVsphereVirtualDiskVolumeSource(
                fs_type=self.fs_type,
                storage_policy_id=self.storage_policy_id,
                storage_policy_name=self.storage_policy_name,
                volume_path=self.volume_path,
            ),
        )


class ExistingVolume(_BaseVolume, _ModelPersistentVolumeClaimVolumeSource):
    def _build_volume(self) -> _ModelVolume:
        return _ModelVolume(
            name=self.name,
            persistent_volume_claim=_ModelPersistentVolumeClaimVolumeSource(
                claim_name=self.claim_name, read_only=self.read_only
            ),
        )


class Volume(_BaseVolume, _ModelPersistentVolumeClaimSpec):
    size: Optional[str] = None  # type: ignore
    resources: Optional[ResourceRequirements] = None
    metadata: Optional[ObjectMeta] = None
    access_modes: Optional[List[AccessMode]] = [AccessMode.read_write_once]  # type: ignore
    storage_class_name: Optional[str] = "standard"

    @validator("name", pre=True, always=True)
    def _check_name(cls, v):
        return v or str(uuid.uuid4())

    @root_validator(pre=True)
    def _merge_reqs(cls, values):
        if "size" in values and "resources" in values:
            resources: ResourceRequirements = values.get("resources")
            if resources.requests is not None:
                if "storage" in resources.requests:
                    pass  # take the storage specification in resources
                else:
                    resources.requests["storage"] = values.get("size")
        elif "resources" not in values:
            assert "size" in values, "at least one of `size` or `resources` must be specified"
            validate_storage_units(cast(str, values.get("size")))
            values["resources"] = ResourceRequirements(requests={"storage": values.get("size")})
        elif "resources" in values:
            resources = cast(ResourceRequirements, values.get("resources"))
            assert resources.requests is not None, "Resource requests are required"
            storage = resources.requests.get("storage")
            assert storage is not None, "At least one of `size` or `resources.requests.storage` must be specified"
            validate_storage_units(cast(str, storage))
        return values

    def _build_persistent_volume_claim_template(self) -> _ModelPersistentVolumeClaimTemplate:
        return _ModelPersistentVolumeClaimTemplate(
            metadata=self.metadata or ObjectMeta(name=self.name),
            spec=_ModelPersistentVolumeClaimSpec(
                access_modes=[str(am.value) for am in self.access_modes] if self.access_modes is not None else None,
                data_source=self.data_source,
                data_source_ref=self.data_source_ref,
                resources=self.resources,
                selector=self.selector,
                storage_class_name=self.storage_class_name,
                volume_mode=self.volume_mode,
                volume_name=self.volume_name,
            ),
        )

    def _build_volume(self) -> _ModelVolume:
        claim = self._build_persistent_volume_claim_template()
        assert claim.metadata is not None, "claim metadata is required"
        return _ModelVolume(
            name=self.name,
            persistent_volume_claim=_ModelPersistentVolumeClaimVolumeSource(
                claim_name=cast(str, claim.metadata.name),
                read_only=self.read_only,
            ),
        )


__all__ = [
    "AccessMode",
    *[c.__name__ for c in _BaseVolume.__subclasses__()],
]