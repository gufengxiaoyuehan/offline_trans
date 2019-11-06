import gzip
import logging
import os
import sys
import tempfile
import click

from offline_trans.docker_archive import DockerManifest

from .docker_transport import export_docker_diff, import_docker_diff, pre_check
from .util import (get_logger, get_manifest_json, get_running_image_hashes,
                   get_tar_path, run_process, save_manifest_json,
                   set_current_dir, set_log_level, set_manifest_path)


@click.group()
@click.option('--debug/--no-debug', default=False, help='toggle debug mode on/off')
@click.option('--manifest', help="base manifest file path")
@click.option('--workdir', help="workdir to find or save files")
def cli(debug, manifest, workdir):
    if debug:
        set_log_level(logging.DEBUG)
    
    if manifest:
        set_manifest_path(manifest)
    
    if workdir:
        set_current_dir(workdir)
    
    click.echo("Debug mode is %s" % ('on' if debug else 'off'))
    


@cli.command()
@click.argument('image_name')
def init(image_name):
    """this will create the ``docker_transport`` in this directory
    and make a snapshot off image given
    """
    image_layers = run_process(f'docker image inspect {image_name} -f "{{{{.RootFS.Layers}}}}"')
    if image_layers.returncode != 0:
        click.echo(f'erorr happens\n{image_layers.stderr.decode()}')
        sys.exit(1)
    
    base_manifest = get_manifest_json(image_name)
    if base_manifest.exists() and click.confirm("file already exist, do you want relpace this?", abort=True):
        base_manifest.unlink()
        click.echo("overwrite orignal file")
        
    click.echo(f" save layers' hash to {base_manifest} ")
    save_manifest_json(image_name)
    click.echo("you can copy this to target machine, make diff-trans base on this later")

@cli.command()
@click.argument('image_name')
def export(image_name):
    """export diff layers with refresh meta info
    """
    base_manifest = get_manifest_json(image_name)
    if not base_manifest.exists():
        click.echo(f'{image_name} not transport before,  init this project by \noffline_trans init')
        sys.exit(0)
    # set logging level first
    curr_layer_hashes = get_running_image_hashes(image_name)
    base_layer_manifest = DockerManifest(base_manifest)
    res_code, reason, _ = pre_check(base_layer_manifest.layer_hashes, curr_layer_hashes)
    if res_code == 1:
        click.confirm(f'{reason}, forward process ?', abort=True)
    elif res_code == 2:
        click.confirm(f'{reason}, may be there are two different layers?, countine or not', abort=True)
    
    export_docker_diff(image_name)
    click.echo("done!") 


@cli.command(name="import")
@click.argument("image_name")
@click.option('--keep-file/--no-keep-file', 'keep_file', default=False, help="donot remove generated tar file")
def import_(image_name, keep_file):
    """import diff layers to base
    """
    diff_image_path = get_tar_path(image_name, 'diff', compress=True)
    if not diff_image_path.exists():
        click.echo(f"diff image {diff_image_path} do not exists")

    base_image = get_manifest_json(image_name)
    if not base_image.exists() and click.confirm(f"base image not exits, save it use `dock save` or abort this process?", abort=True):
        save_manifest_json(image_name)
        
    p_check = run_process(f'docker inspect {image_name}')
    # init import
    if p_check.returncode != 0 and click.confirm(f'no image[{image_name}] found, import anyway?', abort=True):
        fd, tar_file = tempfile.mkstemp()

        with  gzip.GzipFile(diff_image_path, 'rb') as compressed:
            os.write(fd, compressed.read())

        run_process(f'docker load -i {tar_file}')
        
    else:
        image_path = import_docker_diff(image_name)
        p = run_process(f'docker load -i {image_path}')
        if p.returncode != 0:
            click.echo(p.stderr) 
        if not keep_file:
            os.unlink(image_path)
        save_manifest_json(image_name)
        click.echo("done!")


if __name__ == "__main__":
    cli.main()
