__FILENAME__ = autogit
import sublime, sublime_plugin, os, codecs
import shutil
import sys, platform
from os.path import expanduser

# Paths

HOME = expanduser("~")
#PYGIT2_BASEDIR = '/Library/Python/2.7/site-packages/'
PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))

PYGIT2_BASEDIR = os.path.join(PACKAGE_PATH,'site-packages')

AUTOGIT_PATH = '/usr/local/autogit/'

# libgit2_path = os.getenv("LIBGIT2")
#if libgit2_path is None:
#	if os.name == 'nt':
#   	program_files = os.getenv("ProgramFiles")
#		libgit2_path = '%s\libgit2' % program_files
#	else:
#		libgit2_path = '/usr/local'

# What version are we running?

WinOsVersion,_,_,_ = platform.win32_ver()
MacOsVersion,_,_ = platform.mac_ver()
if( WinOsVersion ):
	APPDIR = os.getenv("APPDATA")
	AUTOGIT_PATH = "%s/autogit/" % APPDIR
	AUTOGIT_PATH = AUTOGIT_PATH.replace("\\","/")


elif( MacOsVersion ):
	AUTOGIT_PATH = "%s/Library/Application Support/autogit/" % HOME

if( not os.path.isdir( AUTOGIT_PATH ) ):
	os.makedirs(AUTOGIT_PATH)

print WinOsVersion, MacOsVersion, AUTOGIT_PATH

# Because sublime uses its own python env, set pygit path manually before loading module:
def fixPath():
	for path in sys.path:
		if path == PYGIT2_BASEDIR:
			return
	sys.path.append(PYGIT2_BASEDIR)
fixPath();

print sys.path

#import pygit2
from dulwich.repo import Repo
from dulwich.index import index_entry_from_stat, changes_from_tree
from dulwich.objects import Blob
from dulwich.diff_tree import tree_changes

class ExampleCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.insert(edit, 0, "Hello, World!")

class GitRepository():
	def init(self,path):
		#pygit2.init_repository(path, False)
		if( not os.path.isdir( path ) ):
			os.makedirs(path)
		Repo.init(path)

	def adjustPath(self, gitRoot, filePath):
		drive, path = os.path.splitdrive(filePath)
		if drive:
			path = path.replace("\\","/")
		if( path.startswith("/") ):
			path = path[1:]
		joined = os.path.join( gitRoot, path )
		joined = joined.replace("\\","/")
		return joined

	def dulwichCommit(self, filePath, fullPath, kind):

		git = Repo(AUTOGIT_PATH)
		staged = map(str,[filePath])
		git.stage( staged )

		index = git.open_index()

		try:
			committer = git._get_user_identity()
		except ValueError:
			committer = "autogit"

		try:
			head = git.head()
		except KeyError:
			return git.do_commit( '%s - autogit commit (via dulwich)' % kind, committer=committer)

		changes = list(tree_changes(git, index.commit(git.object_store), git['HEAD'].tree))
		if changes and len(changes) > 0:
			return git.do_commit( '%s - autogit commit (via dulwich)' % kind, committer=committer)
		return None

	def pygit2Commit(self, filePath, kind):

		git = pygit2.Repository(GIT_REPOSITORY_PATH)

		index = git.index
		index.read()
		index.add(filePath)
		#oid = index[filePath]
		index.write();
		
		for entry in index:
			print "added %s %s to index" % (entry.path, entry.hex)

		status = git.status()
		try:
			status[filePath]
		except KeyError:
			# If there is nothing different since last save, git status will report no difference.
			return

		try:			
			HEAD = git.revparse_single('HEAD')
			parents = [HEAD.hex]
		except KeyError:
			parents = []

		commit = git.create_commit(
		    'HEAD',
		    pygit2.Signature('autogit you', 'autogit@ninlabs.com'), 
		    pygit2.Signature('autogit you', 'autogit@ninlabs.com'),
		    '%s - autogit commit' % kind,
		    index.write_tree(),
		    parents
		)

		return commit

class AutoGitEvent(sublime_plugin.EventListener):  

	# this will normally not result in a commit unless it was a first time saving file or file was externally modified.
	def on_pre_save(self, view):  
		
		#body = view.substr(sublime.Region(0, view.size())).encode('utf-8')
		#with open(path,'w') as f:
		#	f.write( body )
		#	f.close()

		commit = self.handleCommit(view, "pre save")
		if commit:
			print "*******", view.file_name(), "pre save - commited"
 
	def on_post_save(self, view):  
		#with codecs.open(view.file_name(), "r", "utf-8") as f:
		#	print f.read()
		commit = self.handleCommit(view, "post save")
		if commit:
			print "*******", view.file_name(), "postsave - commited"

	def handleCommit(self,view, kind):
		repo = GitRepository()
		path = repo.adjustPath( AUTOGIT_PATH, view.file_name() )

		dir = os.path.dirname( path )

		if( not os.path.isdir(dir) ):
			os.makedirs(dir)

		shutil.copy2(view.file_name(),path)

		## rel path is needed for commit
		relPath = path.replace(AUTOGIT_PATH, "")
		if( relPath.startswith("/") ):
			relPath = relPath[1:]


		#return repo.commit(relPath, kind)
		return repo.dulwichCommit(relPath, path, kind)

### Create initial autogit repository if it doesn't exist

GIT_REPOSITORY_PATH = os.path.join( AUTOGIT_PATH, ".git" )
if( not os.path.isdir( GIT_REPOSITORY_PATH ) ):
	repo = GitRepository()
	repo.init(AUTOGIT_PATH)
	print "##### created git repo: " + GIT_REPOSITORY_PATH


########NEW FILE########
__FILENAME__ = client
# client.py -- Implementation of the server side git protocols
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
# Copyright (C) 2008 John Carr
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Client side support for the Git protocol.

The Dulwich client supports the following capabilities:

 * thin-pack
 * multi_ack_detailed
 * multi_ack
 * side-band-64k
 * ofs-delta
 * report-status
 * delete-refs

Known capabilities that are not supported:

 * shallow
 * no-progress
 * include-tag
"""

__docformat__ = 'restructuredText'

from cStringIO import StringIO
import select
import socket
import subprocess
import urllib2
import urlparse

from dulwich.errors import (
    GitProtocolError,
    NotGitRepository,
    SendPackError,
    UpdateRefsError,
    )
from dulwich.protocol import (
    _RBUFSIZE,
    PktLineParser,
    Protocol,
    TCP_GIT_PORT,
    ZERO_SHA,
    extract_capabilities,
    )
from dulwich.pack import (
    write_pack_objects,
    )


# Python 2.6.6 included these in urlparse.uses_netloc upstream. Do
# monkeypatching to enable similar behaviour in earlier Pythons:
for scheme in ('git', 'git+ssh'):
    if scheme not in urlparse.uses_netloc:
        urlparse.uses_netloc.append(scheme)

def _fileno_can_read(fileno):
    """Check if a file descriptor is readable."""
    return len(select.select([fileno], [], [], 0)[0]) > 0

COMMON_CAPABILITIES = ['ofs-delta', 'side-band-64k']
FETCH_CAPABILITIES = ['thin-pack', 'multi_ack', 'multi_ack_detailed'] + COMMON_CAPABILITIES
SEND_CAPABILITIES = ['report-status'] + COMMON_CAPABILITIES


class ReportStatusParser(object):
    """Handle status as reported by servers with the 'report-status' capability.
    """

    def __init__(self):
        self._done = False
        self._pack_status = None
        self._ref_status_ok = True
        self._ref_statuses = []

    def check(self):
        """Check if there were any errors and, if so, raise exceptions.

        :raise SendPackError: Raised when the server could not unpack
        :raise UpdateRefsError: Raised when refs could not be updated
        """
        if self._pack_status not in ('unpack ok', None):
            raise SendPackError(self._pack_status)
        if not self._ref_status_ok:
            ref_status = {}
            ok = set()
            for status in self._ref_statuses:
                if ' ' not in status:
                    # malformed response, move on to the next one
                    continue
                status, ref = status.split(' ', 1)

                if status == 'ng':
                    if ' ' in ref:
                        ref, status = ref.split(' ', 1)
                else:
                    ok.add(ref)
                ref_status[ref] = status
            raise UpdateRefsError('%s failed to update' %
                                  ', '.join([ref for ref in ref_status
                                             if ref not in ok]),
                                  ref_status=ref_status)

    def handle_packet(self, pkt):
        """Handle a packet.

        :raise GitProtocolError: Raised when packets are received after a
            flush packet.
        """
        if self._done:
            raise GitProtocolError("received more data after status report")
        if pkt is None:
            self._done = True
            return
        if self._pack_status is None:
            self._pack_status = pkt.strip()
        else:
            ref_status = pkt.strip()
            self._ref_statuses.append(ref_status)
            if not ref_status.startswith('ok '):
                self._ref_status_ok = False


# TODO(durin42): this doesn't correctly degrade if the server doesn't
# support some capabilities. This should work properly with servers
# that don't support multi_ack.
class GitClient(object):
    """Git smart server client.

    """

    def __init__(self, thin_packs=True, report_activity=None):
        """Create a new GitClient instance.

        :param thin_packs: Whether or not thin packs should be retrieved
        :param report_activity: Optional callback for reporting transport
            activity.
        """
        self._report_activity = report_activity
        self._report_status_parser = None
        self._fetch_capabilities = set(FETCH_CAPABILITIES)
        self._send_capabilities = set(SEND_CAPABILITIES)
        if not thin_packs:
            self._fetch_capabilities.remove('thin-pack')

    def _read_refs(self, proto):
        server_capabilities = None
        refs = {}
        # Receive refs from server
        for pkt in proto.read_pkt_seq():
            (sha, ref) = pkt.rstrip('\n').split(' ', 1)
            if sha == 'ERR':
                raise GitProtocolError(ref)
            if server_capabilities is None:
                (ref, server_capabilities) = extract_capabilities(ref)
            refs[ref] = sha

        if len(refs) == 0:
            return None, set([])
        return refs, set(server_capabilities)

    def send_pack(self, path, determine_wants, generate_pack_contents,
                  progress=None):
        """Upload a pack to a remote repository.

        :param path: Repository path
        :param generate_pack_contents: Function that can return a sequence of the
            shas of the objects to upload.
        :param progress: Optional progress function

        :raises SendPackError: if server rejects the pack data
        :raises UpdateRefsError: if the server supports report-status
                                 and rejects ref updates
        """
        raise NotImplementedError(self.send_pack)

    def fetch(self, path, target, determine_wants=None, progress=None):
        """Fetch into a target repository.

        :param path: Path to fetch from
        :param target: Target repository to fetch into
        :param determine_wants: Optional function to determine what refs
            to fetch
        :param progress: Optional progress function
        :return: remote refs as dictionary
        """
        if determine_wants is None:
            determine_wants = target.object_store.determine_wants_all
        f, commit, abort = target.object_store.add_pack()
        try:
            result = self.fetch_pack(path, determine_wants,
                    target.get_graph_walker(), f.write, progress)
        except:
            abort()
            raise
        else:
            commit()
        return result

    def fetch_pack(self, path, determine_wants, graph_walker, pack_data,
                   progress=None):
        """Retrieve a pack from a git smart server.

        :param determine_wants: Callback that returns list of commits to fetch
        :param graph_walker: Object with next() and ack().
        :param pack_data: Callback called for each bit of data in the pack
        :param progress: Callback for progress reports (strings)
        """
        raise NotImplementedError(self.fetch_pack)

    def _parse_status_report(self, proto):
        unpack = proto.read_pkt_line().strip()
        if unpack != 'unpack ok':
            st = True
            # flush remaining error data
            while st is not None:
                st = proto.read_pkt_line()
            raise SendPackError(unpack)
        statuses = []
        errs = False
        ref_status = proto.read_pkt_line()
        while ref_status:
            ref_status = ref_status.strip()
            statuses.append(ref_status)
            if not ref_status.startswith('ok '):
                errs = True
            ref_status = proto.read_pkt_line()

        if errs:
            ref_status = {}
            ok = set()
            for status in statuses:
                if ' ' not in status:
                    # malformed response, move on to the next one
                    continue
                status, ref = status.split(' ', 1)

                if status == 'ng':
                    if ' ' in ref:
                        ref, status = ref.split(' ', 1)
                else:
                    ok.add(ref)
                ref_status[ref] = status
            raise UpdateRefsError('%s failed to update' %
                                  ', '.join([ref for ref in ref_status
                                             if ref not in ok]),
                                  ref_status=ref_status)

    def _read_side_band64k_data(self, proto, channel_callbacks):
        """Read per-channel data.

        This requires the side-band-64k capability.

        :param proto: Protocol object to read from
        :param channel_callbacks: Dictionary mapping channels to packet
            handlers to use. None for a callback discards channel data.
        """
        for pkt in proto.read_pkt_seq():
            channel = ord(pkt[0])
            pkt = pkt[1:]
            try:
                cb = channel_callbacks[channel]
            except KeyError:
                raise AssertionError('Invalid sideband channel %d' % channel)
            else:
                if cb is not None:
                    cb(pkt)

    def _handle_receive_pack_head(self, proto, capabilities, old_refs, new_refs):
        """Handle the head of a 'git-receive-pack' request.

        :param proto: Protocol object to read from
        :param capabilities: List of negotiated capabilities
        :param old_refs: Old refs, as received from the server
        :param new_refs: New refs
        :return: (have, want) tuple
        """
        want = []
        have = [x for x in old_refs.values() if not x == ZERO_SHA]
        sent_capabilities = False

        for refname in set(new_refs.keys() + old_refs.keys()):
            old_sha1 = old_refs.get(refname, ZERO_SHA)
            new_sha1 = new_refs.get(refname, ZERO_SHA)

            if old_sha1 != new_sha1:
                if sent_capabilities:
                    proto.write_pkt_line('%s %s %s' % (old_sha1, new_sha1,
                                                            refname))
                else:
                    proto.write_pkt_line(
                      '%s %s %s\0%s' % (old_sha1, new_sha1, refname,
                                        ' '.join(capabilities)))
                    sent_capabilities = True
            if new_sha1 not in have and new_sha1 != ZERO_SHA:
                want.append(new_sha1)
        proto.write_pkt_line(None)
        return (have, want)

    def _handle_receive_pack_tail(self, proto, capabilities, progress=None):
        """Handle the tail of a 'git-receive-pack' request.

        :param proto: Protocol object to read from
        :param capabilities: List of negotiated capabilities
        :param progress: Optional progress reporting function
        """
        if "side-band-64k" in capabilities:
            if progress is None:
                progress = lambda x: None
            channel_callbacks = { 2: progress }
            if 'report-status' in capabilities:
                channel_callbacks[1] = PktLineParser(
                    self._report_status_parser.handle_packet).parse
            self._read_side_band64k_data(proto, channel_callbacks)
        else:
            if 'report-status' in capabilities:
                for pkt in proto.read_pkt_seq():
                    self._report_status_parser.handle_packet(pkt)
        if self._report_status_parser is not None:
            self._report_status_parser.check()
        # wait for EOF before returning
        data = proto.read()
        if data:
            raise SendPackError('Unexpected response %r' % data)

    def _handle_upload_pack_head(self, proto, capabilities, graph_walker,
                                 wants, can_read):
        """Handle the head of a 'git-upload-pack' request.

        :param proto: Protocol object to read from
        :param capabilities: List of negotiated capabilities
        :param graph_walker: GraphWalker instance to call .ack() on
        :param wants: List of commits to fetch
        :param can_read: function that returns a boolean that indicates
            whether there is extra graph data to read on proto
        """
        assert isinstance(wants, list) and type(wants[0]) == str
        proto.write_pkt_line('want %s %s\n' % (
            wants[0], ' '.join(capabilities)))
        for want in wants[1:]:
            proto.write_pkt_line('want %s\n' % want)
        proto.write_pkt_line(None)
        have = graph_walker.next()
        while have:
            proto.write_pkt_line('have %s\n' % have)
            if can_read():
                pkt = proto.read_pkt_line()
                parts = pkt.rstrip('\n').split(' ')
                if parts[0] == 'ACK':
                    graph_walker.ack(parts[1])
                    if parts[2] in ('continue', 'common'):
                        pass
                    elif parts[2] == 'ready':
                        break
                    else:
                        raise AssertionError(
                            "%s not in ('continue', 'ready', 'common)" %
                            parts[2])
            have = graph_walker.next()
        proto.write_pkt_line('done\n')

    def _handle_upload_pack_tail(self, proto, capabilities, graph_walker,
                                 pack_data, progress=None, rbufsize=_RBUFSIZE):
        """Handle the tail of a 'git-upload-pack' request.

        :param proto: Protocol object to read from
        :param capabilities: List of negotiated capabilities
        :param graph_walker: GraphWalker instance to call .ack() on
        :param pack_data: Function to call with pack data
        :param progress: Optional progress reporting function
        :param rbufsize: Read buffer size
        """
        pkt = proto.read_pkt_line()
        while pkt:
            parts = pkt.rstrip('\n').split(' ')
            if parts[0] == 'ACK':
                graph_walker.ack(pkt.split(' ')[1])
            if len(parts) < 3 or parts[2] not in (
                    'ready', 'continue', 'common'):
                break
            pkt = proto.read_pkt_line()
        if "side-band-64k" in capabilities:
            if progress is None:
                # Just ignore progress data
                progress = lambda x: None
            self._read_side_band64k_data(proto, {1: pack_data, 2: progress})
            # wait for EOF before returning
            data = proto.read()
            if data:
                raise Exception('Unexpected response %r' % data)
        else:
            while True:
                data = proto.read(rbufsize)
                if data == "":
                    break
                pack_data(data)


class TraditionalGitClient(GitClient):
    """Traditional Git client."""

    def _connect(self, cmd, path):
        """Create a connection to the server.

        This method is abstract - concrete implementations should
        implement their own variant which connects to the server and
        returns an initialized Protocol object with the service ready
        for use and a can_read function which may be used to see if
        reads would block.

        :param cmd: The git service name to which we should connect.
        :param path: The path we should pass to the service.
        """
        raise NotImplementedError()

    def send_pack(self, path, determine_wants, generate_pack_contents,
                  progress=None):
        """Upload a pack to a remote repository.

        :param path: Repository path
        :param generate_pack_contents: Function that can return a sequence of the
            shas of the objects to upload.
        :param progress: Optional callback called with progress updates

        :raises SendPackError: if server rejects the pack data
        :raises UpdateRefsError: if the server supports report-status
                                 and rejects ref updates
        """
        proto, unused_can_read = self._connect('receive-pack', path)
        old_refs, server_capabilities = self._read_refs(proto)
        negotiated_capabilities = self._send_capabilities & server_capabilities

        if 'report-status' in negotiated_capabilities:
            self._report_status_parser = ReportStatusParser()
        report_status_parser = self._report_status_parser

        try:
            new_refs = orig_new_refs = determine_wants(dict(old_refs))
        except:
            proto.write_pkt_line(None)
            raise

        if not 'delete-refs' in server_capabilities:
            # Server does not support deletions. Fail later.
            def remove_del(pair):
                if pair[1] == ZERO_SHA:
                    if 'report-status' in negotiated_capabilities:
                        report_status_parser._ref_statuses.append(
                            'ng %s remote does not support deleting refs'
                            % pair[1])
                        report_status_parser._ref_status_ok = False
                    return False
                else:
                    return True

            new_refs = dict(
                filter(
                    remove_del,
                    [(ref, sha) for ref, sha in new_refs.iteritems()]))

        if new_refs is None:
            proto.write_pkt_line(None)
            return old_refs

        if len(new_refs) == 0 and len(orig_new_refs):
            # NOOP - Original new refs filtered out by policy
            proto.write_pkt_line(None)
            if self._report_status_parser is not None:
                self._report_status_parser.check()
            return old_refs

        (have, want) = self._handle_receive_pack_head(proto,
            negotiated_capabilities, old_refs, new_refs)
        if not want and old_refs == new_refs:
            return new_refs
        objects = generate_pack_contents(have, want)
        if len(objects) > 0:
            entries, sha = write_pack_objects(proto.write_file(), objects)
        elif len(set(new_refs.values()) - set([ZERO_SHA])) > 0:
            # Check for valid create/update refs
            filtered_new_refs = \
                dict([(ref, sha) for ref, sha in new_refs.iteritems()
                     if sha != ZERO_SHA])
            if len(set(filtered_new_refs.iteritems()) -
                    set(old_refs.iteritems())) > 0:
                entries, sha = write_pack_objects(proto.write_file(), objects)

        self._handle_receive_pack_tail(proto, negotiated_capabilities,
            progress)
        return new_refs

    def fetch_pack(self, path, determine_wants, graph_walker, pack_data,
                   progress=None):
        """Retrieve a pack from a git smart server.

        :param determine_wants: Callback that returns list of commits to fetch
        :param graph_walker: Object with next() and ack().
        :param pack_data: Callback called for each bit of data in the pack
        :param progress: Callback for progress reports (strings)
        """
        proto, can_read = self._connect('upload-pack', path)
        refs, server_capabilities = self._read_refs(proto)
        negotiated_capabilities = self._fetch_capabilities & server_capabilities

        if refs is None:
            proto.write_pkt_line(None)
            return refs

        try:
            wants = determine_wants(refs)
        except:
            proto.write_pkt_line(None)
            raise
        if wants is not None:
            wants = [cid for cid in wants if cid != ZERO_SHA]
        if not wants:
            proto.write_pkt_line(None)
            return refs
        self._handle_upload_pack_head(proto, negotiated_capabilities,
            graph_walker, wants, can_read)
        self._handle_upload_pack_tail(proto, negotiated_capabilities,
            graph_walker, pack_data, progress)
        return refs

    def archive(self, path, committish, write_data, progress=None):
        proto, can_read = self._connect('upload-archive', path)
        proto.write_pkt_line("argument %s" % committish)
        proto.write_pkt_line(None)
        pkt = proto.read_pkt_line()
        if pkt == "NACK\n":
            return
        elif pkt == "ACK\n":
            pass
        elif pkt.startswith("ERR "):
            raise GitProtocolError(pkt[4:].rstrip("\n"))
        else:
            raise AssertionError("invalid response %r" % pkt)
        ret = proto.read_pkt_line()
        if ret is not None:
            raise AssertionError("expected pkt tail")
        self._read_side_band64k_data(proto, {1: write_data, 2: progress})


class TCPGitClient(TraditionalGitClient):
    """A Git Client that works over TCP directly (i.e. git://)."""

    def __init__(self, host, port=None, *args, **kwargs):
        if port is None:
            port = TCP_GIT_PORT
        self._host = host
        self._port = port
        TraditionalGitClient.__init__(self, *args, **kwargs)

    def _connect(self, cmd, path):
        sockaddrs = socket.getaddrinfo(self._host, self._port,
            socket.AF_UNSPEC, socket.SOCK_STREAM)
        s = None
        err = socket.error("no address found for %s" % self._host)
        for (family, socktype, proto, canonname, sockaddr) in sockaddrs:
            s = socket.socket(family, socktype, proto)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            try:
                s.connect(sockaddr)
                break
            except socket.error, err:
                if s is not None:
                    s.close()
                s = None
        if s is None:
            raise err
        # -1 means system default buffering
        rfile = s.makefile('rb', -1)
        # 0 means unbuffered
        wfile = s.makefile('wb', 0)
        proto = Protocol(rfile.read, wfile.write,
                         report_activity=self._report_activity)
        if path.startswith("/~"):
            path = path[1:]
        proto.send_cmd('git-%s' % cmd, path, 'host=%s' % self._host)
        return proto, lambda: _fileno_can_read(s)


class SubprocessWrapper(object):
    """A socket-like object that talks to a subprocess via pipes."""

    def __init__(self, proc):
        self.proc = proc
        self.read = proc.stdout.read
        self.write = proc.stdin.write

    def can_read(self):
        if subprocess.mswindows:
            from msvcrt import get_osfhandle
            from win32pipe import PeekNamedPipe
            handle = get_osfhandle(self.proc.stdout.fileno())
            return PeekNamedPipe(handle, 0)[2] != 0
        else:
            return _fileno_can_read(self.proc.stdout.fileno())

    def close(self):
        self.proc.stdin.close()
        self.proc.stdout.close()
        self.proc.wait()


class SubprocessGitClient(TraditionalGitClient):
    """Git client that talks to a server using a subprocess."""

    def __init__(self, *args, **kwargs):
        self._connection = None
        self._stderr = None
        self._stderr = kwargs.get('stderr')
        if 'stderr' in kwargs:
            del kwargs['stderr']
        TraditionalGitClient.__init__(self, *args, **kwargs)

    def _connect(self, service, path):
        import subprocess
        argv = ['git', service, path]
        p = SubprocessWrapper(
            subprocess.Popen(argv, bufsize=0, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=self._stderr))
        return Protocol(p.read, p.write,
                        report_activity=self._report_activity), p.can_read


class SSHVendor(object):
    """A client side SSH implementation."""

    def connect_ssh(self, host, command, username=None, port=None):
        import warnings
        warnings.warn(
            "SSHVendor.connect_ssh has been renamed to SSHVendor.run_command",
            DeprecationWarning)
        return self.run_command(host, command, username=username, port=port)

    def run_command(self, host, command, username=None, port=None):
        """Connect to an SSH server.

        Run a command remotely and return a file-like object for interaction
        with the remote command.

        :param host: Host name
        :param command: Command to run
        :param username: Optional ame of user to log in as
        :param port: Optional SSH port to use
        """
        raise NotImplementedError(self.run_command)


class SubprocessSSHVendor(SSHVendor):
    """SSH vendor that shells out to the local 'ssh' command."""

    def run_command(self, host, command, username=None, port=None):
        import subprocess
        #FIXME: This has no way to deal with passwords..
        args = ['ssh', '-x']
        if port is not None:
            args.extend(['-p', str(port)])
        if username is not None:
            host = '%s@%s' % (username, host)
        args.append(host)
        proc = subprocess.Popen(args + command,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        return SubprocessWrapper(proc)


try:
    import paramiko
except ImportError:
    pass
else:
    import threading

    class ParamikoWrapper(object):
        STDERR_READ_N = 2048  # 2k

        def __init__(self, client, channel, progress_stderr=None):
            self.client = client
            self.channel = channel
            self.progress_stderr = progress_stderr
            self.should_monitor = bool(progress_stderr) or True
            self.monitor_thread = None
            self.stderr = ''

            # Channel must block
            self.channel.setblocking(True)

            # Start
            if self.should_monitor:
                self.monitor_thread = threading.Thread(target=self.monitor_stderr)
                self.monitor_thread.start()

        def monitor_stderr(self):
            while self.should_monitor:
                # Block and read
                data = self.read_stderr(self.STDERR_READ_N)

                # Socket closed
                if not data:
                    self.should_monitor = False
                    break

                # Emit data
                if self.progress_stderr:
                    self.progress_stderr(data)

                # Append to buffer
                self.stderr += data

        def stop_monitoring(self):
            # Stop StdErr thread
            if self.should_monitor:
                self.should_monitor = False
                self.monitor_thread.join()

                # Get left over data
                data = self.channel.in_stderr_buffer.empty()
                self.stderr += data

        def can_read(self):
            return self.channel.recv_ready()

        def write(self, data):
            return self.channel.sendall(data)

        def read_stderr(self, n):
            return self.channel.recv_stderr(n)

        def read(self, n=None):
            data = self.channel.recv(n)
            data_len = len(data)

            # Closed socket
            if not data:
                return

            # Read more if needed
            if n and data_len < n:
                diff_len = n - data_len
                return data + self.read(diff_len)
            return data

        def close(self):
            self.channel.close()
            self.stop_monitoring()

        def __del__(self):
            self.close()

    class ParamikoSSHVendor(object):

        def run_command(self, host, command, username=None, port=None,
                progress_stderr=None, **kwargs):
            client = paramiko.SSHClient()

            policy = paramiko.client.MissingHostKeyPolicy()
            client.set_missing_host_key_policy(policy)
            client.connect(host, username=username, port=port, **kwargs)

            # Open SSH session
            channel = client.get_transport().open_session()

            # Run commands
            apply(channel.exec_command, command)

            return ParamikoWrapper(client, channel,
                    progress_stderr=progress_stderr)


# Can be overridden by users
get_ssh_vendor = SubprocessSSHVendor


class SSHGitClient(TraditionalGitClient):

    def __init__(self, host, port=None, username=None, *args, **kwargs):
        self.host = host
        self.port = port
        self.username = username
        TraditionalGitClient.__init__(self, *args, **kwargs)
        self.alternative_paths = {}

    def _get_cmd_path(self, cmd):
        return self.alternative_paths.get(cmd, 'git-%s' % cmd)

    def _connect(self, cmd, path):
        if path.startswith("/~"):
            path = path[1:]
        con = get_ssh_vendor().run_command(
            self.host, ["%s '%s'" % (self._get_cmd_path(cmd), path)],
            port=self.port, username=self.username)
        return (Protocol(con.read, con.write, report_activity=self._report_activity),
                con.can_read)


class HttpGitClient(GitClient):

    def __init__(self, base_url, dumb=None, *args, **kwargs):
        self.base_url = base_url.rstrip("/") + "/"
        self.dumb = dumb
        GitClient.__init__(self, *args, **kwargs)

    def _get_url(self, path):
        return urlparse.urljoin(self.base_url, path).rstrip("/") + "/"

    def _http_request(self, url, headers={}, data=None):
        req = urllib2.Request(url, headers=headers, data=data)
        try:
            resp = self._perform(req)
        except urllib2.HTTPError as e:
            if e.code == 404:
                raise NotGitRepository()
            if e.code != 200:
                raise GitProtocolError("unexpected http response %d" % e.code)
        return resp

    def _perform(self, req):
        """Perform a HTTP request.

        This is provided so subclasses can provide their own version.

        :param req: urllib2.Request instance
        :return: matching response
        """
        return urllib2.urlopen(req)

    def _discover_references(self, service, url):
        assert url[-1] == "/"
        url = urlparse.urljoin(url, "info/refs")
        headers = {}
        if self.dumb != False:
            url += "?service=%s" % service
            headers["Content-Type"] = "application/x-%s-request" % service
        resp = self._http_request(url, headers)
        self.dumb = (not resp.info().gettype().startswith("application/x-git-"))
        proto = Protocol(resp.read, None)
        if not self.dumb:
            # The first line should mention the service
            pkts = list(proto.read_pkt_seq())
            if pkts != [('# service=%s\n' % service)]:
                raise GitProtocolError(
                    "unexpected first line %r from smart server" % pkts)
        return self._read_refs(proto)

    def _smart_request(self, service, url, data):
        assert url[-1] == "/"
        url = urlparse.urljoin(url, service)
        headers = {"Content-Type": "application/x-%s-request" % service}
        resp = self._http_request(url, headers, data)
        if resp.info().gettype() != ("application/x-%s-result" % service):
            raise GitProtocolError("Invalid content-type from server: %s"
                % resp.info().gettype())
        return resp

    def send_pack(self, path, determine_wants, generate_pack_contents,
                  progress=None):
        """Upload a pack to a remote repository.

        :param path: Repository path
        :param generate_pack_contents: Function that can return a sequence of the
            shas of the objects to upload.
        :param progress: Optional progress function

        :raises SendPackError: if server rejects the pack data
        :raises UpdateRefsError: if the server supports report-status
                                 and rejects ref updates
        """
        url = self._get_url(path)
        old_refs, server_capabilities = self._discover_references(
            "git-receive-pack", url)
        negotiated_capabilities = self._send_capabilities & server_capabilities

        if 'report-status' in negotiated_capabilities:
            self._report_status_parser = ReportStatusParser()

        new_refs = determine_wants(dict(old_refs))
        if new_refs is None:
            return old_refs
        if self.dumb:
            raise NotImplementedError(self.fetch_pack)
        req_data = StringIO()
        req_proto = Protocol(None, req_data.write)
        (have, want) = self._handle_receive_pack_head(
            req_proto, negotiated_capabilities, old_refs, new_refs)
        if not want and old_refs == new_refs:
            return new_refs
        objects = generate_pack_contents(have, want)
        if len(objects) > 0:
            entries, sha = write_pack_objects(req_proto.write_file(), objects)
        resp = self._smart_request("git-receive-pack", url,
            data=req_data.getvalue())
        resp_proto = Protocol(resp.read, None)
        self._handle_receive_pack_tail(resp_proto, negotiated_capabilities,
            progress)
        return new_refs

    def fetch_pack(self, path, determine_wants, graph_walker, pack_data,
                   progress=None):
        """Retrieve a pack from a git smart server.

        :param determine_wants: Callback that returns list of commits to fetch
        :param graph_walker: Object with next() and ack().
        :param pack_data: Callback called for each bit of data in the pack
        :param progress: Callback for progress reports (strings)
        :return: Dictionary with the refs of the remote repository
        """
        url = self._get_url(path)
        refs, server_capabilities = self._discover_references(
            "git-upload-pack", url)
        negotiated_capabilities = self._fetch_capabilities & server_capabilities
        wants = determine_wants(refs)
        if wants is not None:
            wants = [cid for cid in wants if cid != ZERO_SHA]
        if not wants:
            return refs
        if self.dumb:
            raise NotImplementedError(self.send_pack)
        req_data = StringIO()
        req_proto = Protocol(None, req_data.write)
        self._handle_upload_pack_head(req_proto,
            negotiated_capabilities, graph_walker, wants,
            lambda: False)
        resp = self._smart_request("git-upload-pack", url,
            data=req_data.getvalue())
        resp_proto = Protocol(resp.read, None)
        self._handle_upload_pack_tail(resp_proto, negotiated_capabilities,
            graph_walker, pack_data, progress)
        return refs


def get_transport_and_path(uri, **kwargs):
    """Obtain a git client from a URI or path.

    :param uri: URI or path
    :param thin_packs: Whether or not thin packs should be retrieved
    :param report_activity: Optional callback for reporting transport
        activity.
    :return: Tuple with client instance and relative path.
    """
    parsed = urlparse.urlparse(uri)
    if parsed.scheme == 'git':
        return (TCPGitClient(parsed.hostname, port=parsed.port, **kwargs),
                parsed.path)
    elif parsed.scheme == 'git+ssh':
        path = parsed.path
        if path.startswith('/'):
            path = parsed.path[1:]
        return SSHGitClient(parsed.hostname, port=parsed.port,
                            username=parsed.username, **kwargs), path
    elif parsed.scheme in ('http', 'https'):
        return HttpGitClient(urlparse.urlunparse(parsed), **kwargs), parsed.path

    if parsed.scheme and not parsed.netloc:
        # SSH with no user@, zero or one leading slash.
        return SSHGitClient(parsed.scheme, **kwargs), parsed.path
    elif parsed.scheme:
        raise ValueError('Unknown git protocol scheme: %s' % parsed.scheme)
    elif '@' in parsed.path and ':' in parsed.path:
        # SSH with user@host:foo.
        user_host, path = parsed.path.split(':')
        user, host = user_host.rsplit('@')
        return SSHGitClient(host, username=user, **kwargs), path

    # Otherwise, assume it's a local path.
    return SubprocessGitClient(**kwargs), uri

########NEW FILE########
__FILENAME__ = config
# config.py - Reading and writing Git config files
# Copyright (C) 2011 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Reading and writing Git configuration files.

TODO:
 * preserve formatting when updating configuration files
 * treat subsection names as case-insensitive for [branch.foo] style
   subsections
"""

import errno
import os
import re

try:
    from collections import OrderedDict
except ImportError:
    from dulwich._compat import OrderedDict

from UserDict import DictMixin

from dulwich.file import GitFile


class Config(object):
    """A Git configuration."""

    def get(self, section, name):
        """Retrieve the contents of a configuration setting.

        :param section: Tuple with section name and optional subsection namee
        :param subsection: Subsection name
        :return: Contents of the setting
        :raise KeyError: if the value is not set
        """
        raise NotImplementedError(self.get)

    def get_boolean(self, section, name, default=None):
        """Retrieve a configuration setting as boolean.

        :param section: Tuple with section name and optional subsection namee
        :param name: Name of the setting, including section and possible
            subsection.
        :return: Contents of the setting
        :raise KeyError: if the value is not set
        """
        try:
            value = self.get(section, name)
        except KeyError:
            return default
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        raise ValueError("not a valid boolean string: %r" % value)

    def set(self, section, name, value):
        """Set a configuration value.

        :param name: Name of the configuration value, including section
            and optional subsection
        :param: Value of the setting
        """
        raise NotImplementedError(self.set)


class ConfigDict(Config, DictMixin):
    """Git configuration stored in a dictionary."""

    def __init__(self, values=None):
        """Create a new ConfigDict."""
        if values is None:
            values = OrderedDict()
        self._values = values

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._values)

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            other._values == self._values)

    def __getitem__(self, key):
        return self._values[key]

    def __setitem__(self, key, value):
        self._values[key] = value

    def keys(self):
        return self._values.keys()

    @classmethod
    def _parse_setting(cls, name):
        parts = name.split(".")
        if len(parts) == 3:
            return (parts[0], parts[1], parts[2])
        else:
            return (parts[0], None, parts[1])

    def get(self, section, name):
        if isinstance(section, basestring):
            section = (section, )
        if len(section) > 1:
            try:
                return self._values[section][name]
            except KeyError:
                pass
        return self._values[(section[0],)][name]

    def set(self, section, name, value):
        if isinstance(section, basestring):
            section = (section, )
        self._values.setdefault(section, OrderedDict())[name] = value


def _format_string(value):
    if (value.startswith(" ") or
        value.startswith("\t") or
        value.endswith(" ") or
        value.endswith("\t")):
        return '"%s"' % _escape_value(value)
    return _escape_value(value)


def _parse_string(value):
    value = value.strip()
    ret = []
    block = []
    in_quotes  = False
    for c in value:
        if c == "\"":
            in_quotes = (not in_quotes)
            ret.append(_unescape_value("".join(block)))
            block = []
        elif c in ("#", ";") and not in_quotes:
            # the rest of the line is a comment
            break
        else:
            block.append(c)

    if in_quotes:
        raise ValueError("value starts with quote but lacks end quote")

    ret.append(_unescape_value("".join(block)).rstrip())

    return "".join(ret)


def _unescape_value(value):
    """Unescape a value."""
    def unescape(c):
        return {
            "\\\\": "\\",
            "\\\"": "\"",
            "\\n": "\n",
            "\\t": "\t",
            "\\b": "\b",
            }[c.group(0)]
    return re.sub(r"(\\.)", unescape, value)


def _escape_value(value):
    """Escape a value."""
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t").replace("\"", "\\\"")


def _check_variable_name(name):
    for c in name:
        if not c.isalnum() and c != '-':
            return False
    return True


def _check_section_name(name):
    for c in name:
        if not c.isalnum() and c not in ('-', '.'):
            return False
    return True


def _strip_comments(line):
    line = line.split("#")[0]
    line = line.split(";")[0]
    return line


class ConfigFile(ConfigDict):
    """A Git configuration file, like .git/config or ~/.gitconfig.
    """

    @classmethod
    def from_file(cls, f):
        """Read configuration from a file-like object."""
        ret = cls()
        section = None
        setting = None
        for lineno, line in enumerate(f.readlines()):
            line = line.lstrip()
            if setting is None:
                if len(line) > 0 and line[0] == "[":
                    line = _strip_comments(line).rstrip()
                    last = line.index("]")
                    if last == -1:
                        raise ValueError("expected trailing ]")
                    pts = line[1:last].split(" ", 1)
                    line = line[last+1:]
                    pts[0] = pts[0].lower()
                    if len(pts) == 2:
                        if pts[1][0] != "\"" or pts[1][-1] != "\"":
                            raise ValueError(
                                "Invalid subsection " + pts[1])
                        else:
                            pts[1] = pts[1][1:-1]
                        if not _check_section_name(pts[0]):
                            raise ValueError("invalid section name %s" %
                                             pts[0])
                        section = (pts[0], pts[1])
                    else:
                        if not _check_section_name(pts[0]):
                            raise ValueError("invalid section name %s" %
                                    pts[0])
                        pts = pts[0].split(".", 1)
                        if len(pts) == 2:
                            section = (pts[0], pts[1])
                        else:
                            section = (pts[0], )
                    ret._values[section] = OrderedDict()
                if _strip_comments(line).strip() == "":
                    continue
                if section is None:
                    raise ValueError("setting %r without section" % line)
                try:
                    setting, value = line.split("=", 1)
                except ValueError:
                    setting = line
                    value = "true"
                setting = setting.strip().lower()
                if not _check_variable_name(setting):
                    raise ValueError("invalid variable name %s" % setting)
                if value.endswith("\\\n"):
                    value = value[:-2]
                    continuation = True
                else:
                    continuation = False
                value = _parse_string(value)
                ret._values[section][setting] = value
                if not continuation:
                    setting = None
            else: # continuation line
                if line.endswith("\\\n"):
                    line = line[:-2]
                    continuation = True
                else:
                    continuation = False
                value = _parse_string(line)
                ret._values[section][setting] += value
                if not continuation:
                    setting = None
        return ret

    @classmethod
    def from_path(cls, path):
        """Read configuration from a file on disk."""
        f = GitFile(path, 'rb')
        try:
            ret = cls.from_file(f)
            ret.path = path
            return ret
        finally:
            f.close()

    def write_to_path(self, path=None):
        """Write configuration to a file on disk."""
        if path is None:
            path = self.path
        f = GitFile(path, 'wb')
        try:
            self.write_to_file(f)
        finally:
            f.close()

    def write_to_file(self, f):
        """Write configuration to a file-like object."""
        for section, values in self._values.iteritems():
            try:
                section_name, subsection_name = section
            except ValueError:
                (section_name, ) = section
                subsection_name = None
            if subsection_name is None:
                f.write("[%s]\n" % section_name)
            else:
                f.write("[%s \"%s\"]\n" % (section_name, subsection_name))
            for key, value in values.iteritems():
                f.write("\t%s = %s\n" % (key, _escape_value(value)))


class StackedConfig(Config):
    """Configuration which reads from multiple config files.."""

    def __init__(self, backends, writable=None):
        self.backends = backends
        self.writable = writable

    def __repr__(self):
        return "<%s for %r>" % (self.__class__.__name__, self.backends)

    @classmethod
    def default_backends(cls):
        """Retrieve the default configuration.

        This will look in the repository configuration (if for_path is
        specified), the users' home directory and the system
        configuration.
        """
        paths = []
        paths.append(os.path.expanduser("~/.gitconfig"))
        paths.append("/etc/gitconfig")
        backends = []
        for path in paths:
            try:
                cf = ConfigFile.from_path(path)
            except (IOError, OSError), e:
                if e.errno != errno.ENOENT:
                    raise
                else:
                    continue
            backends.append(cf)
        return backends

    def get(self, section, name):
        for backend in self.backends:
            try:
                return backend.get(section, name)
            except KeyError:
                pass
        raise KeyError(name)

    def set(self, section, name, value):
        if self.writable is None:
            raise NotImplementedError(self.set)
        return self.writable.set(section, name, value)

########NEW FILE########
__FILENAME__ = diff_tree
# diff_tree.py -- Utilities for diffing files and trees.
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Utilities for diffing files and trees."""

try:
    from collections import defaultdict
except ImportError:
    from dulwich._compat import defaultdict

from cStringIO import StringIO
import itertools
import stat

from dulwich._compat import (
    namedtuple,
    )
from dulwich.objects import (
    S_ISGITLINK,
    TreeEntry,
    )

# TreeChange type constants.
CHANGE_ADD = 'add'
CHANGE_MODIFY = 'modify'
CHANGE_DELETE = 'delete'
CHANGE_RENAME = 'rename'
CHANGE_COPY = 'copy'
CHANGE_UNCHANGED = 'unchanged'

RENAME_CHANGE_TYPES = (CHANGE_RENAME, CHANGE_COPY)

_NULL_ENTRY = TreeEntry(None, None, None)

_MAX_SCORE = 100
RENAME_THRESHOLD = 60
MAX_FILES = 200
REWRITE_THRESHOLD = None


class TreeChange(namedtuple('TreeChange', ['type', 'old', 'new'])):
    """Named tuple a single change between two trees."""

    @classmethod
    def add(cls, new):
        return cls(CHANGE_ADD, _NULL_ENTRY, new)

    @classmethod
    def delete(cls, old):
        return cls(CHANGE_DELETE, old, _NULL_ENTRY)


def _tree_entries(path, tree):
    result = []
    if not tree:
        return result
    for entry in tree.iteritems(name_order=True):
        result.append(entry.in_path(path))
    return result


def _merge_entries(path, tree1, tree2):
    """Merge the entries of two trees.

    :param path: A path to prepend to all tree entry names.
    :param tree1: The first Tree object to iterate, or None.
    :param tree2: The second Tree object to iterate, or None.
    :return: A list of pairs of TreeEntry objects for each pair of entries in
        the trees. If an entry exists in one tree but not the other, the other
        entry will have all attributes set to None. If neither entry's path is
        None, they are guaranteed to match.
    """
    entries1 = _tree_entries(path, tree1)
    entries2 = _tree_entries(path, tree2)
    i1 = i2 = 0
    len1 = len(entries1)
    len2 = len(entries2)

    result = []
    while i1 < len1 and i2 < len2:
        entry1 = entries1[i1]
        entry2 = entries2[i2]
        if entry1.path < entry2.path:
            result.append((entry1, _NULL_ENTRY))
            i1 += 1
        elif entry1.path > entry2.path:
            result.append((_NULL_ENTRY, entry2))
            i2 += 1
        else:
            result.append((entry1, entry2))
            i1 += 1
            i2 += 1
    for i in xrange(i1, len1):
        result.append((entries1[i], _NULL_ENTRY))
    for i in xrange(i2, len2):
        result.append((_NULL_ENTRY, entries2[i]))
    return result


def _is_tree(entry):
    mode = entry.mode
    if mode is None:
        return False
    return stat.S_ISDIR(mode)


def walk_trees(store, tree1_id, tree2_id, prune_identical=False):
    """Recursively walk all the entries of two trees.

    Iteration is depth-first pre-order, as in e.g. os.walk.

    :param store: An ObjectStore for looking up objects.
    :param tree1_id: The SHA of the first Tree object to iterate, or None.
    :param tree2_id: The SHA of the second Tree object to iterate, or None.
    :param prune_identical: If True, identical subtrees will not be walked.
    :return: Iterator over Pairs of TreeEntry objects for each pair of entries
        in the trees and their subtrees recursively. If an entry exists in one
        tree but not the other, the other entry will have all attributes set
        to None. If neither entry's path is None, they are guaranteed to
        match.
    """
    # This could be fairly easily generalized to >2 trees if we find a use case.
    mode1 = tree1_id and stat.S_IFDIR or None
    mode2 = tree2_id and stat.S_IFDIR or None
    todo = [(TreeEntry('', mode1, tree1_id), TreeEntry('', mode2, tree2_id))]
    while todo:
        entry1, entry2 = todo.pop()
        is_tree1 = _is_tree(entry1)
        is_tree2 = _is_tree(entry2)
        if prune_identical and is_tree1 and is_tree2 and entry1 == entry2:
            continue

        tree1 = is_tree1 and store[entry1.sha] or None
        tree2 = is_tree2 and store[entry2.sha] or None
        path = entry1.path or entry2.path
        todo.extend(reversed(_merge_entries(path, tree1, tree2)))
        yield entry1, entry2


def _skip_tree(entry):
    if entry.mode is None or stat.S_ISDIR(entry.mode):
        return _NULL_ENTRY
    return entry


def tree_changes(store, tree1_id, tree2_id, want_unchanged=False,
                 rename_detector=None):
    """Find the differences between the contents of two trees.

    :param store: An ObjectStore for looking up objects.
    :param tree1_id: The SHA of the source tree.
    :param tree2_id: The SHA of the target tree.
    :param want_unchanged: If True, include TreeChanges for unmodified entries
        as well.
    :param rename_detector: RenameDetector object for detecting renames.
    :return: Iterator over TreeChange instances for each change between the
        source and target tree.
    """
    if (rename_detector is not None and tree1_id is not None and
        tree2_id is not None):
        for change in rename_detector.changes_with_renames(
          tree1_id, tree2_id, want_unchanged=want_unchanged):
            yield change
        return

    entries = walk_trees(store, tree1_id, tree2_id,
                         prune_identical=(not want_unchanged))
    for entry1, entry2 in entries:
        if entry1 == entry2 and not want_unchanged:
            continue

        # Treat entries for trees as missing.
        entry1 = _skip_tree(entry1)
        entry2 = _skip_tree(entry2)

        if entry1 != _NULL_ENTRY and entry2 != _NULL_ENTRY:
            if stat.S_IFMT(entry1.mode) != stat.S_IFMT(entry2.mode):
                # File type changed: report as delete/add.
                yield TreeChange.delete(entry1)
                entry1 = _NULL_ENTRY
                change_type = CHANGE_ADD
            elif entry1 == entry2:
                change_type = CHANGE_UNCHANGED
            else:
                change_type = CHANGE_MODIFY
        elif entry1 != _NULL_ENTRY:
            change_type = CHANGE_DELETE
        elif entry2 != _NULL_ENTRY:
            change_type = CHANGE_ADD
        else:
            # Both were None because at least one was a tree.
            continue
        yield TreeChange(change_type, entry1, entry2)


def _all_eq(seq, key, value):
    for e in seq:
        if key(e) != value:
            return False
    return True


def _all_same(seq, key):
    return _all_eq(seq[1:], key, key(seq[0]))


def tree_changes_for_merge(store, parent_tree_ids, tree_id,
                           rename_detector=None):
    """Get the tree changes for a merge tree relative to all its parents.

    :param store: An ObjectStore for looking up objects.
    :param parent_tree_ids: An iterable of the SHAs of the parent trees.
    :param tree_id: The SHA of the merge tree.
    :param rename_detector: RenameDetector object for detecting renames.

    :return: Iterator over lists of TreeChange objects, one per conflicted path
        in the merge.

        Each list contains one element per parent, with the TreeChange for that
        path relative to that parent. An element may be None if it never existed
        in one parent and was deleted in two others.

        A path is only included in the output if it is a conflict, i.e. its SHA
        in the merge tree is not found in any of the parents, or in the case of
        deletes, if not all of the old SHAs match.
    """
    all_parent_changes = [tree_changes(store, t, tree_id,
                                       rename_detector=rename_detector)
                          for t in parent_tree_ids]
    num_parents = len(parent_tree_ids)
    changes_by_path = defaultdict(lambda: [None] * num_parents)

    # Organize by path.
    for i, parent_changes in enumerate(all_parent_changes):
        for change in parent_changes:
            if change.type == CHANGE_DELETE:
                path = change.old.path
            else:
                path = change.new.path
            changes_by_path[path][i] = change

    old_sha = lambda c: c.old.sha
    change_type = lambda c: c.type

    # Yield only conflicting changes.
    for _, changes in sorted(changes_by_path.iteritems()):
        assert len(changes) == num_parents
        have = [c for c in changes if c is not None]
        if _all_eq(have, change_type, CHANGE_DELETE):
            if not _all_same(have, old_sha):
                yield changes
        elif not _all_same(have, change_type):
            yield changes
        elif None not in changes:
            # If no change was found relative to one parent, that means the SHA
            # must have matched the SHA in that parent, so it is not a conflict.
            yield changes


_BLOCK_SIZE = 64


def _count_blocks(obj):
    """Count the blocks in an object.

    Splits the data into blocks either on lines or <=64-byte chunks of lines.

    :param obj: The object to count blocks for.
    :return: A dict of block hashcode -> total bytes occurring.
    """
    block_counts = defaultdict(int)
    block = StringIO()
    n = 0

    # Cache attrs as locals to avoid expensive lookups in the inner loop.
    block_write = block.write
    block_seek = block.seek
    block_truncate = block.truncate
    block_getvalue = block.getvalue

    for c in itertools.chain(*obj.as_raw_chunks()):
        block_write(c)
        n += 1
        if c == '\n' or n == _BLOCK_SIZE:
            value = block_getvalue()
            block_counts[hash(value)] += len(value)
            block_seek(0)
            block_truncate()
            n = 0
    if n > 0:
        last_block = block_getvalue()
        block_counts[hash(last_block)] += len(last_block)
    return block_counts


def _common_bytes(blocks1, blocks2):
    """Count the number of common bytes in two block count dicts.

    :param block1: The first dict of block hashcode -> total bytes.
    :param block2: The second dict of block hashcode -> total bytes.
    :return: The number of bytes in common between blocks1 and blocks2. This is
        only approximate due to possible hash collisions.
    """
    # Iterate over the smaller of the two dicts, since this is symmetrical.
    if len(blocks1) > len(blocks2):
        blocks1, blocks2 = blocks2, blocks1
    score = 0
    for block, count1 in blocks1.iteritems():
        count2 = blocks2.get(block)
        if count2:
            score += min(count1, count2)
    return score


def _similarity_score(obj1, obj2, block_cache=None):
    """Compute a similarity score for two objects.

    :param obj1: The first object to score.
    :param obj2: The second object to score.
    :param block_cache: An optional dict of SHA to block counts to cache results
        between calls.
    :return: The similarity score between the two objects, defined as the number
        of bytes in common between the two objects divided by the maximum size,
        scaled to the range 0-100.
    """
    if block_cache is None:
        block_cache = {}
    if obj1.id not in block_cache:
        block_cache[obj1.id] = _count_blocks(obj1)
    if obj2.id not in block_cache:
        block_cache[obj2.id] = _count_blocks(obj2)

    common_bytes = _common_bytes(block_cache[obj1.id], block_cache[obj2.id])
    max_size = max(obj1.raw_length(), obj2.raw_length())
    if not max_size:
        return _MAX_SCORE
    return int(float(common_bytes) * _MAX_SCORE / max_size)


def _tree_change_key(entry):
    # Sort by old path then new path. If only one exists, use it for both keys.
    path1 = entry.old.path
    path2 = entry.new.path
    if path1 is None:
        path1 = path2
    if path2 is None:
        path2 = path1
    return (path1, path2)


class RenameDetector(object):
    """Object for handling rename detection between two trees."""

    def __init__(self, store, rename_threshold=RENAME_THRESHOLD,
                 max_files=MAX_FILES,
                 rewrite_threshold=REWRITE_THRESHOLD,
                 find_copies_harder=False):
        """Initialize the rename detector.

        :param store: An ObjectStore for looking up objects.
        :param rename_threshold: The threshold similarity score for considering
            an add/delete pair to be a rename/copy; see _similarity_score.
        :param max_files: The maximum number of adds and deletes to consider, or
            None for no limit. The detector is guaranteed to compare no more
            than max_files ** 2 add/delete pairs. This limit is provided because
            rename detection can be quadratic in the project size. If the limit
            is exceeded, no content rename detection is attempted.
        :param rewrite_threshold: The threshold similarity score below which a
            modify should be considered a delete/add, or None to not break
            modifies; see _similarity_score.
        :param find_copies_harder: If True, consider unmodified files when
            detecting copies.
        """
        self._store = store
        self._rename_threshold = rename_threshold
        self._rewrite_threshold = rewrite_threshold
        self._max_files = max_files
        self._find_copies_harder = find_copies_harder
        self._want_unchanged = False

    def _reset(self):
        self._adds = []
        self._deletes = []
        self._changes = []

    def _should_split(self, change):
        if (self._rewrite_threshold is None or change.type != CHANGE_MODIFY or
            change.old.sha == change.new.sha):
            return False
        old_obj = self._store[change.old.sha]
        new_obj = self._store[change.new.sha]
        return _similarity_score(old_obj, new_obj) < self._rewrite_threshold

    def _add_change(self, change):
        if change.type == CHANGE_ADD:
            self._adds.append(change)
        elif change.type == CHANGE_DELETE:
            self._deletes.append(change)
        elif self._should_split(change):
            self._deletes.append(TreeChange.delete(change.old))
            self._adds.append(TreeChange.add(change.new))
        elif ((self._find_copies_harder and change.type == CHANGE_UNCHANGED)
              or change.type == CHANGE_MODIFY):
            # Treat all modifies as potential deletes for rename detection,
            # but don't split them (to avoid spurious renames). Setting
            # find_copies_harder means we treat unchanged the same as
            # modified.
            self._deletes.append(change)
        else:
            self._changes.append(change)

    def _collect_changes(self, tree1_id, tree2_id):
        want_unchanged = self._find_copies_harder or self._want_unchanged
        for change in tree_changes(self._store, tree1_id, tree2_id,
                                   want_unchanged=want_unchanged):
            self._add_change(change)

    def _prune(self, add_paths, delete_paths):
        self._adds = [a for a in self._adds if a.new.path not in add_paths]
        self._deletes = [d for d in self._deletes
                         if d.old.path not in delete_paths]

    def _find_exact_renames(self):
        add_map = defaultdict(list)
        for add in self._adds:
            add_map[add.new.sha].append(add.new)
        delete_map = defaultdict(list)
        for delete in self._deletes:
            # Keep track of whether the delete was actually marked as a delete.
            # If not, it needs to be marked as a copy.
            is_delete = delete.type == CHANGE_DELETE
            delete_map[delete.old.sha].append((delete.old, is_delete))

        add_paths = set()
        delete_paths = set()
        for sha, sha_deletes in delete_map.iteritems():
            sha_adds = add_map[sha]
            for (old, is_delete), new in itertools.izip(sha_deletes, sha_adds):
                if stat.S_IFMT(old.mode) != stat.S_IFMT(new.mode):
                    continue
                if is_delete:
                    delete_paths.add(old.path)
                add_paths.add(new.path)
                new_type = is_delete and CHANGE_RENAME or CHANGE_COPY
                self._changes.append(TreeChange(new_type, old, new))

            num_extra_adds = len(sha_adds) - len(sha_deletes)
            # TODO(dborowitz): Less arbitrary way of dealing with extra copies.
            old = sha_deletes[0][0]
            if num_extra_adds:
                for new in sha_adds[-num_extra_adds:]:
                    add_paths.add(new.path)
                    self._changes.append(TreeChange(CHANGE_COPY, old, new))
        self._prune(add_paths, delete_paths)

    def _should_find_content_renames(self):
        return len(self._adds) * len(self._deletes) <= self._max_files ** 2

    def _rename_type(self, check_paths, delete, add):
        if check_paths and delete.old.path == add.new.path:
            # If the paths match, this must be a split modify, so make sure it
            # comes out as a modify.
            return CHANGE_MODIFY
        elif delete.type != CHANGE_DELETE:
            # If it's in deletes but not marked as a delete, it must have been
            # added due to find_copies_harder, and needs to be marked as a copy.
            return CHANGE_COPY
        return CHANGE_RENAME

    def _find_content_rename_candidates(self):
        candidates = self._candidates = []
        # TODO: Optimizations:
        #  - Compare object sizes before counting blocks.
        #  - Skip if delete's S_IFMT differs from all adds.
        #  - Skip if adds or deletes is empty.
        # Match C git's behavior of not attempting to find content renames if
        # the matrix size exceeds the threshold.
        if not self._should_find_content_renames():
            return

        check_paths = self._rename_threshold is not None
        for delete in self._deletes:
            if S_ISGITLINK(delete.old.mode):
                continue  # Git links don't exist in this repo.
            old_sha = delete.old.sha
            old_obj = self._store[old_sha]
            old_blocks = _count_blocks(old_obj)
            for add in self._adds:
                if stat.S_IFMT(delete.old.mode) != stat.S_IFMT(add.new.mode):
                    continue
                new_obj = self._store[add.new.sha]
                score = _similarity_score(old_obj, new_obj,
                                          block_cache={old_sha: old_blocks})
                if score > self._rename_threshold:
                    new_type = self._rename_type(check_paths, delete, add)
                    rename = TreeChange(new_type, delete.old, add.new)
                    candidates.append((-score, rename))

    def _choose_content_renames(self):
        # Sort scores from highest to lowest, but keep names in ascending order.
        self._candidates.sort()

        delete_paths = set()
        add_paths = set()
        for _, change in self._candidates:
            new_path = change.new.path
            if new_path in add_paths:
                continue
            old_path = change.old.path
            orig_type = change.type
            if old_path in delete_paths:
                change = TreeChange(CHANGE_COPY, change.old, change.new)

            # If the candidate was originally a copy, that means it came from a
            # modified or unchanged path, so we don't want to prune it.
            if orig_type != CHANGE_COPY:
                delete_paths.add(old_path)
            add_paths.add(new_path)
            self._changes.append(change)
        self._prune(add_paths, delete_paths)

    def _join_modifies(self):
        if self._rewrite_threshold is None:
            return

        modifies = {}
        delete_map = dict((d.old.path, d) for d in self._deletes)
        for add in self._adds:
            path = add.new.path
            delete = delete_map.get(path)
            if (delete is not None and
              stat.S_IFMT(delete.old.mode) == stat.S_IFMT(add.new.mode)):
                modifies[path] = TreeChange(CHANGE_MODIFY, delete.old, add.new)

        self._adds = [a for a in self._adds if a.new.path not in modifies]
        self._deletes = [a for a in self._deletes if a.new.path not in modifies]
        self._changes += modifies.values()

    def _sorted_changes(self):
        result = []
        result.extend(self._adds)
        result.extend(self._deletes)
        result.extend(self._changes)
        result.sort(key=_tree_change_key)
        return result

    def _prune_unchanged(self):
        if self._want_unchanged:
            return
        self._deletes = [d for d in self._deletes if d.type != CHANGE_UNCHANGED]

    def changes_with_renames(self, tree1_id, tree2_id, want_unchanged=False):
        """Iterate TreeChanges between two tree SHAs, with rename detection."""
        self._reset()
        self._want_unchanged = want_unchanged
        self._collect_changes(tree1_id, tree2_id)
        self._find_exact_renames()
        self._find_content_rename_candidates()
        self._choose_content_renames()
        self._join_modifies()
        self._prune_unchanged()
        return self._sorted_changes()


# Hold on to the pure-python implementations for testing.
_is_tree_py = _is_tree
_merge_entries_py = _merge_entries
_count_blocks_py = _count_blocks
try:
    # Try to import C versions
    from dulwich._diff_tree import _is_tree, _merge_entries, _count_blocks
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = errors
# errors.py -- errors for dulwich
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Dulwich-related exception classes and utility functions."""

import binascii


class ChecksumMismatch(Exception):
    """A checksum didn't match the expected contents."""

    def __init__(self, expected, got, extra=None):
        if len(expected) == 20:
            expected = binascii.hexlify(expected)
        if len(got) == 20:
            got = binascii.hexlify(got)
        self.expected = expected
        self.got = got
        self.extra = extra
        if self.extra is None:
            Exception.__init__(self,
                "Checksum mismatch: Expected %s, got %s" % (expected, got))
        else:
            Exception.__init__(self,
                "Checksum mismatch: Expected %s, got %s; %s" %
                (expected, got, extra))


class WrongObjectException(Exception):
    """Baseclass for all the _ is not a _ exceptions on objects.

    Do not instantiate directly.

    Subclasses should define a type_name attribute that indicates what
    was expected if they were raised.
    """

    def __init__(self, sha, *args, **kwargs):
        Exception.__init__(self, "%s is not a %s" % (sha, self.type_name))


class NotCommitError(WrongObjectException):
    """Indicates that the sha requested does not point to a commit."""

    type_name = 'commit'


class NotTreeError(WrongObjectException):
    """Indicates that the sha requested does not point to a tree."""

    type_name = 'tree'


class NotTagError(WrongObjectException):
    """Indicates that the sha requested does not point to a tag."""

    type_name = 'tag'


class NotBlobError(WrongObjectException):
    """Indicates that the sha requested does not point to a blob."""

    type_name = 'blob'


class MissingCommitError(Exception):
    """Indicates that a commit was not found in the repository"""

    def __init__(self, sha, *args, **kwargs):
        self.sha = sha
        Exception.__init__(self, "%s is not in the revision store" % sha)


class ObjectMissing(Exception):
    """Indicates that a requested object is missing."""

    def __init__(self, sha, *args, **kwargs):
        Exception.__init__(self, "%s is not in the pack" % sha)


class ApplyDeltaError(Exception):
    """Indicates that applying a delta failed."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class NotGitRepository(Exception):
    """Indicates that no Git repository was found."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class GitProtocolError(Exception):
    """Git protocol exception."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class SendPackError(GitProtocolError):
    """An error occurred during send_pack."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class UpdateRefsError(GitProtocolError):
    """The server reported errors updating refs."""

    def __init__(self, *args, **kwargs):
        self.ref_status = kwargs.pop('ref_status')
        Exception.__init__(self, *args, **kwargs)


class HangupException(GitProtocolError):
    """Hangup exception."""

    def __init__(self):
        Exception.__init__(self,
            "The remote server unexpectedly closed the connection.")


class UnexpectedCommandError(GitProtocolError):
    """Unexpected command received in a proto line."""

    def __init__(self, command):
        if command is None:
            command = 'flush-pkt'
        else:
            command = 'command %s' % command
        GitProtocolError.__init__(self, 'Protocol got unexpected %s' % command)


class FileFormatException(Exception):
    """Base class for exceptions relating to reading git file formats."""


class PackedRefsException(FileFormatException):
    """Indicates an error parsing a packed-refs file."""


class ObjectFormatException(FileFormatException):
    """Indicates an error parsing an object."""


class NoIndexPresent(Exception):
    """No index is present."""


class CommitError(Exception):
    """An error occurred while performing a commit."""


class RefFormatError(Exception):
    """Indicates an invalid ref name."""


class HookError(Exception):
    """An error occurred while executing a hook."""

########NEW FILE########
__FILENAME__ = fastexport
# __init__.py -- Fast export/import functionality
# Copyright (C) 2010 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.


"""Fast export/import functionality."""

from dulwich.index import (
    commit_tree,
    )
from dulwich.objects import (
    Blob,
    Commit,
    Tag,
    )
from fastimport import (
    commands,
    errors as fastimport_errors,
    parser,
    processor,
    )

import stat


def split_email(text):
    (name, email) = text.rsplit(" <", 1)
    return (name, email.rstrip(">"))


class GitFastExporter(object):
    """Generate a fast-export output stream for Git objects."""

    def __init__(self, outf, store):
        self.outf = outf
        self.store = store
        self.markers = {}
        self._marker_idx = 0

    def print_cmd(self, cmd):
        self.outf.write("%r\n" % cmd)

    def _allocate_marker(self):
        self._marker_idx+=1
        return str(self._marker_idx)

    def _export_blob(self, blob):
        marker = self._allocate_marker()
        self.markers[marker] = blob.id
        return (commands.BlobCommand(marker, blob.data), marker)

    def emit_blob(self, blob):
        (cmd, marker) = self._export_blob(blob)
        self.print_cmd(cmd)
        return marker

    def _iter_files(self, base_tree, new_tree):
        for (old_path, new_path), (old_mode, new_mode), (old_hexsha, new_hexsha) in \
                self.store.tree_changes(base_tree, new_tree):
            if new_path is None:
                yield commands.FileDeleteCommand(old_path)
                continue
            if not stat.S_ISDIR(new_mode):
                blob = self.store[new_hexsha]
                marker = self.emit_blob(blob)
            if old_path != new_path and old_path is not None:
                yield commands.FileRenameCommand(old_path, new_path)
            if old_mode != new_mode or old_hexsha != new_hexsha:
                yield commands.FileModifyCommand(new_path, new_mode, marker, None)

    def _export_commit(self, commit, ref, base_tree=None):
        file_cmds = list(self._iter_files(base_tree, commit.tree))
        marker = self._allocate_marker()
        if commit.parents:
            from_ = commit.parents[0]
            merges = commit.parents[1:]
        else:
            from_ = None
            merges = []
        author, author_email = split_email(commit.author)
        committer, committer_email = split_email(commit.committer)
        cmd = commands.CommitCommand(ref, marker,
            (author, author_email, commit.author_time, commit.author_timezone),
            (committer, committer_email, commit.commit_time, commit.commit_timezone),
            commit.message, from_, merges, file_cmds)
        return (cmd, marker)

    def emit_commit(self, commit, ref, base_tree=None):
        cmd, marker = self._export_commit(commit, ref, base_tree)
        self.print_cmd(cmd)
        return marker


class GitImportProcessor(processor.ImportProcessor):
    """An import processor that imports into a Git repository using Dulwich.

    """
    # FIXME: Batch creation of objects?

    def __init__(self, repo, params=None, verbose=False, outf=None):
        processor.ImportProcessor.__init__(self, params, verbose)
        self.repo = repo
        self.last_commit = None
        self.markers = {}
        self._contents = {}

    def import_stream(self, stream):
        p = parser.ImportParser(stream)
        self.process(p.iter_commands)
        return self.markers

    def blob_handler(self, cmd):
        """Process a BlobCommand."""
        blob = Blob.from_string(cmd.data)
        self.repo.object_store.add_object(blob)
        if cmd.mark:
            self.markers[cmd.mark] = blob.id

    def checkpoint_handler(self, cmd):
        """Process a CheckpointCommand."""
        pass

    def commit_handler(self, cmd):
        """Process a CommitCommand."""
        commit = Commit()
        if cmd.author is not None:
            author = cmd.author
        else:
            author = cmd.committer
        (author_name, author_email, author_timestamp, author_timezone) = author
        (committer_name, committer_email, commit_timestamp, commit_timezone) = cmd.committer
        commit.author = "%s <%s>" % (author_name, author_email)
        commit.author_timezone = author_timezone
        commit.author_time = int(author_timestamp)
        commit.committer = "%s <%s>" % (committer_name, committer_email)
        commit.commit_timezone = commit_timezone
        commit.commit_time = int(commit_timestamp)
        commit.message = cmd.message
        commit.parents = []
        if cmd.from_:
            self._reset_base(cmd.from_)
        for filecmd in cmd.iter_files():
            if filecmd.name == "filemodify":
                if filecmd.data is not None:
                    blob = Blob.from_string(filecmd.data)
                    self.repo.object_store.add(blob)
                    blob_id = blob.id
                else:
                    assert filecmd.dataref[0] == ":", "non-marker refs not supported yet"
                    blob_id = self.markers[filecmd.dataref[1:]]
                self._contents[filecmd.path] = (filecmd.mode, blob_id)
            elif filecmd.name == "filedelete":
                del self._contents[filecmd.path]
            elif filecmd.name == "filecopy":
                self._contents[filecmd.dest_path] = self._contents[filecmd.src_path]
            elif filecmd.name == "filerename":
                self._contents[filecmd.new_path] = self._contents[filecmd.old_path]
                del self._contents[filecmd.old_path]
            elif filecmd.name == "filedeleteall":
                self._contents = {}
            else:
                raise Exception("Command %s not supported" % filecmd.name)
        commit.tree = commit_tree(self.repo.object_store,
            ((path, hexsha, mode) for (path, (mode, hexsha)) in
                self._contents.iteritems()))
        if self.last_commit is not None:
            commit.parents.append(self.last_commit)
        commit.parents += cmd.merges
        self.repo.object_store.add_object(commit)
        self.repo[cmd.ref] = commit.id
        self.last_commit = commit.id
        if cmd.mark:
            self.markers[cmd.mark] = commit.id

    def progress_handler(self, cmd):
        """Process a ProgressCommand."""
        pass

    def _reset_base(self, commit_id):
        if self.last_commit == commit_id:
            return
        self.last_commit = commit_id
        self._contents = {}
        tree_id = self.repo[commit_id].tree
        for (path, mode, hexsha) in (
                self.repo.object_store.iter_tree_contents(tree_id)):
            self._contents[path] = (mode, hexsha)

    def reset_handler(self, cmd):
        """Process a ResetCommand."""
        self._reset_base(cmd.from_)
        self.rep.refs[cmd.from_] = cmd.id

    def tag_handler(self, cmd):
        """Process a TagCommand."""
        tag = Tag()
        tag.tagger = cmd.tagger
        tag.message = cmd.message
        tag.name = cmd.tag
        self.repo.add_object(tag)
        self.repo.refs["refs/tags/" + tag.name] = tag.id

    def feature_handler(self, cmd):
        """Process a FeatureCommand."""
        raise fastimport_errors.UnknownFeature(cmd.feature_name)

########NEW FILE########
__FILENAME__ = file
# file.py -- Safe access to git files
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Safe access to git files."""

import errno
import os
import tempfile

def ensure_dir_exists(dirname):
    """Ensure a directory exists, creating if necessary."""
    try:
        os.makedirs(dirname)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise


def fancy_rename(oldname, newname):
    """Rename file with temporary backup file to rollback if rename fails"""
    if not os.path.exists(newname):
        try:
            os.rename(oldname, newname)
        except OSError, e:
            raise
        return

    # destination file exists
    try:
        (fd, tmpfile) = tempfile.mkstemp(".tmp", prefix=oldname+".", dir=".")
        os.close(fd)
        os.remove(tmpfile)
    except OSError, e:
        # either file could not be created (e.g. permission problem)
        # or could not be deleted (e.g. rude virus scanner)
        raise
    try:
        os.rename(newname, tmpfile)
    except OSError, e:
        raise   # no rename occurred
    try:
        os.rename(oldname, newname)
    except OSError, e:
        os.rename(tmpfile, newname)
        raise
    os.remove(tmpfile)


def GitFile(filename, mode='rb', bufsize=-1):
    """Create a file object that obeys the git file locking protocol.

    :return: a builtin file object or a _GitFile object

    :note: See _GitFile for a description of the file locking protocol.

    Only read-only and write-only (binary) modes are supported; r+, w+, and a
    are not.  To read and write from the same file, you can take advantage of
    the fact that opening a file for write does not actually open the file you
    request.
    """
    if 'a' in mode:
        raise IOError('append mode not supported for Git files')
    if '+' in mode:
        raise IOError('read/write mode not supported for Git files')
    if 'b' not in mode:
        raise IOError('text mode not supported for Git files')
    if 'w' in mode:
        return _GitFile(filename, mode, bufsize)
    else:
        return file(filename, mode, bufsize)


class _GitFile(object):
    """File that follows the git locking protocol for writes.

    All writes to a file foo will be written into foo.lock in the same
    directory, and the lockfile will be renamed to overwrite the original file
    on close.

    :note: You *must* call close() or abort() on a _GitFile for the lock to be
        released. Typically this will happen in a finally block.
    """

    PROXY_PROPERTIES = set(['closed', 'encoding', 'errors', 'mode', 'name',
                            'newlines', 'softspace'])
    PROXY_METHODS = ('__iter__', 'flush', 'fileno', 'isatty', 'next', 'read',
                     'readline', 'readlines', 'xreadlines', 'seek', 'tell',
                     'truncate', 'write', 'writelines')
    def __init__(self, filename, mode, bufsize):
        self._filename = filename
        self._lockfilename = '%s.lock' % self._filename
        fd = os.open(self._lockfilename,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        self._file = os.fdopen(fd, mode, bufsize)
        self._closed = False

        for method in self.PROXY_METHODS:
            setattr(self, method, getattr(self._file, method))

    def abort(self):
        """Close and discard the lockfile without overwriting the target.

        If the file is already closed, this is a no-op.
        """
        if self._closed:
            return
        self._file.close()
        try:
            os.remove(self._lockfilename)
            self._closed = True
        except OSError, e:
            # The file may have been removed already, which is ok.
            if e.errno != errno.ENOENT:
                raise
            self._closed = True

    def close(self):
        """Close this file, saving the lockfile over the original.

        :note: If this method fails, it will attempt to delete the lockfile.
            However, it is not guaranteed to do so (e.g. if a filesystem becomes
            suddenly read-only), which will prevent future writes to this file
            until the lockfile is removed manually.
        :raises OSError: if the original file could not be overwritten. The lock
            file is still closed, so further attempts to write to the same file
            object will raise ValueError.
        """
        if self._closed:
            return
        self._file.close()
        try:
            try:
                os.rename(self._lockfilename, self._filename)
            except OSError, e:
                # Windows versions prior to Vista don't support atomic renames
                if e.errno != errno.EEXIST:
                    raise
                fancy_rename(self._lockfilename, self._filename)
        finally:
            self.abort()

    def __getattr__(self, name):
        """Proxy property calls to the underlying file."""
        if name in self.PROXY_PROPERTIES:
            return getattr(self._file, name)
        raise AttributeError(name)

########NEW FILE########
__FILENAME__ = hooks
# hooks.py -- for dealing with git hooks
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Access to hooks."""

import os
import subprocess
import tempfile
import warnings

from dulwich.errors import (
    HookError,
)


class Hook(object):
    """Generic hook object."""

    def execute(elf, *args):
        """Execute the hook with the given args

        :param args: argument list to hook
        :raise HookError: hook execution failure
        :return: a hook may return a useful value
        """
        raise NotImplementedError(self.execute)


class ShellHook(Hook):
    """Hook by executable file

    Implements standard githooks(5) [0]:

    [0] http://www.kernel.org/pub/software/scm/git/docs/githooks.html
    """

    def __init__(self, name, path, numparam,
                 pre_exec_callback=None, post_exec_callback=None):
        """Setup shell hook definition

        :param name: name of hook for error messages
        :param path: absolute path to executable file
        :param numparam: number of requirements parameters
        :param pre_exec_callback: closure for setup before execution
            Defaults to None. Takes in the variable argument list from the
            execute functions and returns a modified argument list for the
            shell hook.
        :param post_exec_callback: closure for cleanup after execution
            Defaults to None. Takes in a boolean for hook success and the
            modified argument list and returns the final hook return value
            if applicable
        """
        self.name = name
        self.filepath = path
        self.numparam = numparam

        self.pre_exec_callback = pre_exec_callback
        self.post_exec_callback = post_exec_callback

    def execute(self, *args):
        """Execute the hook with given args"""

        if len(args) != self.numparam:
            raise HookError("Hook %s executed with wrong number of args. \
                            Expected %d. Saw %d. %s"
                            % (self.name, self.numparam, len(args)))

        if (self.pre_exec_callback is not None):
            args = self.pre_exec_callback(*args)

        try:
            ret = subprocess.call([self.filepath] + list(args))
            if ret != 0:
                if (self.post_exec_callback is not None):
                    self.post_exec_callback(0, *args)
                raise HookError("Hook %s exited with non-zero status"
                                % (self.name))
            if (self.post_exec_callback is not None):
                return self.post_exec_callback(1, *args)
        except OSError:  # no file. silent failure.
            if (self.post_exec_callback is not None):
                self.post_exec_callback(0, *args)


class PreCommitShellHook(ShellHook):
    """pre-commit shell hook"""

    def __init__(self, controldir):
        filepath = os.path.join(controldir, 'hooks', 'pre-commit')

        ShellHook.__init__(self, 'pre-commit', filepath, 0)


class PostCommitShellHook(ShellHook):
    """post-commit shell hook"""

    def __init__(self, controldir):
        filepath = os.path.join(controldir, 'hooks', 'post-commit')

        ShellHook.__init__(self, 'post-commit', filepath, 0)


class CommitMsgShellHook(ShellHook):
    """commit-msg shell hook

    :param args[0]: commit message
    :return: new commit message or None
    """

    def __init__(self, controldir):
        filepath = os.path.join(controldir, 'hooks', 'commit-msg')

        def prepare_msg(*args):
            (fd, path) = tempfile.mkstemp()

            f = os.fdopen(fd, 'wb')
            try:
                f.write(args[0])
            finally:
                f.close()

            return (path,)

        def clean_msg(success, *args):
            if success:
                with open(args[0], 'rb') as f:
                    new_msg = f.read()
                os.unlink(args[0])
                return new_msg
            os.unlink(args[0])

        ShellHook.__init__(self, 'commit-msg', filepath, 1,
                           prepare_msg, clean_msg)

########NEW FILE########
__FILENAME__ = index
# index.py -- File parser/writer for the git index file
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your opinion) any later version of the license.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Parser for the git index file format."""

import errno
import os
import stat
import struct

from dulwich.file import GitFile
from dulwich.objects import (
    S_IFGITLINK,
    S_ISGITLINK,
    Tree,
    hex_to_sha,
    sha_to_hex,
    )
from dulwich.pack import (
    SHA1Reader,
    SHA1Writer,
    )


def pathsplit(path):
    """Split a /-delimited path into a directory part and a basename.

    :param path: The path to split.
    :return: Tuple with directory name and basename
    """
    try:
        (dirname, basename) = path.rsplit("/", 1)
    except ValueError:
        return ("", path)
    else:
        return (dirname, basename)


def pathjoin(*args):
    """Join a /-delimited path.

    """
    return "/".join([p for p in args if p])


def read_cache_time(f):
    """Read a cache time.

    :param f: File-like object to read from
    :return: Tuple with seconds and nanoseconds
    """
    return struct.unpack(">LL", f.read(8))


def write_cache_time(f, t):
    """Write a cache time.

    :param f: File-like object to write to
    :param t: Time to write (as int, float or tuple with secs and nsecs)
    """
    if isinstance(t, int):
        t = (t, 0)
    elif isinstance(t, float):
        (secs, nsecs) = divmod(t, 1.0)
        t = (int(secs), int(nsecs * 1000000000))
    elif not isinstance(t, tuple):
        raise TypeError(t)
    f.write(struct.pack(">LL", *t))


def read_cache_entry(f):
    """Read an entry from a cache file.

    :param f: File-like object to read from
    :return: tuple with: device, inode, mode, uid, gid, size, sha, flags
    """
    beginoffset = f.tell()
    ctime = read_cache_time(f)
    mtime = read_cache_time(f)
    (dev, ino, mode, uid, gid, size, sha, flags, ) = \
        struct.unpack(">LLLLLL20sH", f.read(20 + 4 * 6 + 2))
    name = f.read((flags & 0x0fff))
    # Padding:
    real_size = ((f.tell() - beginoffset + 8) & ~7)
    data = f.read((beginoffset + real_size) - f.tell())
    return (name, ctime, mtime, dev, ino, mode, uid, gid, size,
            sha_to_hex(sha), flags & ~0x0fff)


def write_cache_entry(f, entry):
    """Write an index entry to a file.

    :param f: File object
    :param entry: Entry to write, tuple with:
        (name, ctime, mtime, dev, ino, mode, uid, gid, size, sha, flags)
    """
    beginoffset = f.tell()
    (name, ctime, mtime, dev, ino, mode, uid, gid, size, sha, flags) = entry
    write_cache_time(f, ctime)
    write_cache_time(f, mtime)
    flags = len(name) | (flags &~ 0x0fff)
    f.write(struct.pack(">LLLLLL20sH", dev, ino, mode, uid, gid, size, hex_to_sha(sha), flags))
    f.write(name)
    real_size = ((f.tell() - beginoffset + 8) & ~7)
    f.write("\0" * ((beginoffset + real_size) - f.tell()))


def read_index(f):
    """Read an index file, yielding the individual entries."""
    header = f.read(4)
    if header != "DIRC":
        raise AssertionError("Invalid index file header: %r" % header)
    (version, num_entries) = struct.unpack(">LL", f.read(4 * 2))
    assert version in (1, 2)
    for i in range(num_entries):
        yield read_cache_entry(f)


def read_index_dict(f):
    """Read an index file and return it as a dictionary.

    :param f: File object to read from
    """
    ret = {}
    for x in read_index(f):
        ret[x[0]] = tuple(x[1:])
    return ret


def write_index(f, entries):
    """Write an index file.

    :param f: File-like object to write to
    :param entries: Iterable over the entries to write
    """
    f.write("DIRC")
    f.write(struct.pack(">LL", 2, len(entries)))
    for x in entries:
        write_cache_entry(f, x)


def write_index_dict(f, entries):
    """Write an index file based on the contents of a dictionary.

    """
    entries_list = []
    for name in sorted(entries):
        entries_list.append((name,) + tuple(entries[name]))
    write_index(f, entries_list)


def cleanup_mode(mode):
    """Cleanup a mode value.

    This will return a mode that can be stored in a tree object.

    :param mode: Mode to clean up.
    """
    if stat.S_ISLNK(mode):
        return stat.S_IFLNK
    elif stat.S_ISDIR(mode):
        return stat.S_IFDIR
    elif S_ISGITLINK(mode):
        return S_IFGITLINK
    ret = stat.S_IFREG | 0644
    ret |= (mode & 0111)
    return ret


class Index(object):
    """A Git Index file."""

    def __init__(self, filename):
        """Open an index file.

        :param filename: Path to the index file
        """
        self._filename = filename
        self.clear()
        self.read()

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._filename)

    def write(self):
        """Write current contents of index to disk."""
        f = GitFile(self._filename, 'wb')
        try:
            f = SHA1Writer(f)
            write_index_dict(f, self._byname)
        finally:
            f.close()

    def read(self):
        """Read current contents of index from disk."""
        if not os.path.exists(self._filename):
            return
        f = GitFile(self._filename, 'rb')
        try:
            f = SHA1Reader(f)
            for x in read_index(f):
                self[x[0]] = tuple(x[1:])
            # FIXME: Additional data?
            f.read(os.path.getsize(self._filename)-f.tell()-20)
            f.check_sha()
        finally:
            f.close()

    def __len__(self):
        """Number of entries in this index file."""
        return len(self._byname)

    def __getitem__(self, name):
        """Retrieve entry by relative path.

        :return: tuple with (ctime, mtime, dev, ino, mode, uid, gid, size, sha, flags)
        """
        return self._byname[name]

    def __iter__(self):
        """Iterate over the paths in this index."""
        return iter(self._byname)

    def get_sha1(self, path):
        """Return the (git object) SHA1 for the object at a path."""
        return self[path][-2]

    def get_mode(self, path):
        """Return the POSIX file mode for the object at a path."""
        return self[path][-6]

    def iterblobs(self):
        """Iterate over path, sha, mode tuples for use with commit_tree."""
        for path in self:
            entry = self[path]
            yield path, entry[-2], cleanup_mode(entry[-6])

    def clear(self):
        """Remove all contents from this index."""
        self._byname = {}

    def __setitem__(self, name, x):
        assert isinstance(name, str)
        assert len(x) == 10
        # Remove the old entry if any
        self._byname[name] = x

    def __delitem__(self, name):
        assert isinstance(name, str)
        del self._byname[name]

    def iteritems(self):
        return self._byname.iteritems()

    def update(self, entries):
        for name, value in entries.iteritems():
            self[name] = value

    def changes_from_tree(self, object_store, tree, want_unchanged=False):
        """Find the differences between the contents of this index and a tree.

        :param object_store: Object store to use for retrieving tree contents
        :param tree: SHA1 of the root tree
        :param want_unchanged: Whether unchanged files should be reported
        :return: Iterator over tuples with (oldpath, newpath), (oldmode, newmode), (oldsha, newsha)
        """
        def lookup_entry(path):
            entry = self[path]
            return entry[-2], entry[-6]
        for (name, mode, sha) in changes_from_tree(self._byname.keys(),
                lookup_entry, object_store, tree,
                want_unchanged=want_unchanged):
            yield (name, mode, sha)

    def commit(self, object_store):
        """Create a new tree from an index.

        :param object_store: Object store to save the tree in
        :return: Root tree SHA
        """
        return commit_tree(object_store, self.iterblobs())


def commit_tree(object_store, blobs):
    """Commit a new tree.

    :param object_store: Object store to add trees to
    :param blobs: Iterable over blob path, sha, mode entries
    :return: SHA1 of the created tree.
    """

    trees = {"": {}}

    def add_tree(path):
        if path in trees:
            return trees[path]
        dirname, basename = pathsplit(path)
        t = add_tree(dirname)
        assert isinstance(basename, str)
        newtree = {}
        t[basename] = newtree
        trees[path] = newtree
        return newtree

    for path, sha, mode in blobs:
        tree_path, basename = pathsplit(path)
        tree = add_tree(tree_path)
        tree[basename] = (mode, sha)

    def build_tree(path):
        tree = Tree()
        for basename, entry in trees[path].iteritems():
            if type(entry) == dict:
                mode = stat.S_IFDIR
                sha = build_tree(pathjoin(path, basename))
            else:
                (mode, sha) = entry
            tree.add(basename, mode, sha)
        object_store.add_object(tree)
        return tree.id
    return build_tree("")


def commit_index(object_store, index):
    """Create a new tree from an index.

    :param object_store: Object store to save the tree in
    :param index: Index file
    :note: This function is deprecated, use index.commit() instead.
    :return: Root tree sha.
    """
    return commit_tree(object_store, index.iterblobs())


def changes_from_tree(names, lookup_entry, object_store, tree,
        want_unchanged=False):
    """Find the differences between the contents of a tree and
    a working copy.

    :param names: Iterable of names in the working copy
    :param lookup_entry: Function to lookup an entry in the working copy
    :param object_store: Object store to use for retrieving tree contents
    :param tree: SHA1 of the root tree, or None for an empty tree
    :param want_unchanged: Whether unchanged files should be reported
    :return: Iterator over tuples with (oldpath, newpath), (oldmode, newmode),
        (oldsha, newsha)
    """
    other_names = set(names)

    if tree is not None:
        for (name, mode, sha) in object_store.iter_tree_contents(tree):
            try:
                (other_sha, other_mode) = lookup_entry(name)
            except KeyError:
                # Was removed
                yield ((name, None), (mode, None), (sha, None))
            else:
                other_names.remove(name)
                if (want_unchanged or other_sha != sha or other_mode != mode):
                    yield ((name, name), (mode, other_mode), (sha, other_sha))

    # Mention added files
    for name in other_names:
        (other_sha, other_mode) = lookup_entry(name)
        yield ((None, name), (None, other_mode), (None, other_sha))


def index_entry_from_stat(stat_val, hex_sha, flags, mode=None):
    """Create a new index entry from a stat value.

    :param stat_val: POSIX stat_result instance
    :param hex_sha: Hex sha of the object
    :param flags: Index flags
    """
    if mode is None:
        mode = cleanup_mode(stat_val.st_mode)
    return (stat_val.st_ctime, stat_val.st_mtime, stat_val.st_dev,
            stat_val.st_ino, mode, stat_val.st_uid,
            stat_val.st_gid, stat_val.st_size, hex_sha, flags)


def build_index_from_tree(prefix, index_path, object_store, tree_id,
                          honor_filemode=True):
    """Generate and materialize index from a tree

    :param tree_id: Tree to materialize
    :param prefix: Target dir for materialized index files
    :param index_path: Target path for generated index
    :param object_store: Non-empty object store holding tree contents
    :param honor_filemode: An optional flag to honor core.filemode setting in
        config file, default is core.filemode=True, change executable bit

    :note:: existing index is wiped and contents are not merged
        in a working dir. Suiteable only for fresh clones.
    """

    index = Index(index_path)

    for entry in object_store.iter_tree_contents(tree_id):
        full_path = os.path.join(prefix, entry.path)

        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        # FIXME: Merge new index into working tree
        if stat.S_ISLNK(entry.mode):
            # FIXME: This will fail on Windows. What should we do instead?
            src_path = object_store[entry.sha].as_raw_string()
            try:
                os.symlink(src_path, full_path)
            except OSError, e:
                if e.errno == errno.EEXIST:
                    os.unlink(full_path)
                    os.symlink(src_path, full_path)
                else:
                    raise
        else:
            f = open(full_path, 'wb')
            try:
                # Write out file
                f.write(object_store[entry.sha].as_raw_string())
            finally:
                f.close()

            if honor_filemode:
                os.chmod(full_path, entry.mode)

        # Add file to index
        st = os.lstat(full_path)
        index[entry.path] = index_entry_from_stat(st, entry.sha, 0)

    index.write()

########NEW FILE########
__FILENAME__ = log_utils
# log_utils.py -- Logging utilities for Dulwich
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.

"""Logging utilities for Dulwich.

Any module that uses logging needs to do compile-time initialization to set up
the logging environment. Since Dulwich is also used as a library, clients may
not want to see any logging output. In that case, we need to use a special
handler to suppress spurious warnings like "No handlers could be found for
logger dulwich.foo".

For details on the _NullHandler approach, see:
http://docs.python.org/library/logging.html#configuring-logging-for-a-library

For many modules, the only function from the logging module they need is
getLogger; this module exports that function for convenience. If a calling
module needs something else, it can import the standard logging module directly.
"""

import logging
import sys

getLogger = logging.getLogger


class _NullHandler(logging.Handler):
    """No-op logging handler to avoid unexpected logging warnings."""

    def emit(self, record):
        pass


_NULL_HANDLER = _NullHandler()
_DULWICH_LOGGER = getLogger('dulwich')
_DULWICH_LOGGER.addHandler(_NULL_HANDLER)


def default_logging_config():
    """Set up the default Dulwich loggers."""
    remove_null_handler()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format='%(asctime)s %(levelname)s: %(message)s')


def remove_null_handler():
    """Remove the null handler from the Dulwich loggers.

    If a caller wants to set up logging using something other than
    default_logging_config, calling this function first is a minor optimization
    to avoid the overhead of using the _NullHandler.
    """
    _DULWICH_LOGGER.removeHandler(_NULL_HANDLER)

########NEW FILE########
__FILENAME__ = lru_cache
# lru_cache.py -- Simple LRU cache for dulwich
# Copyright (C) 2006, 2008 Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""A simple least-recently-used (LRU) cache."""

_null_key = object()

class _LRUNode(object):
    """This maintains the linked-list which is the lru internals."""

    __slots__ = ('prev', 'next_key', 'key', 'value', 'cleanup', 'size')

    def __init__(self, key, value, cleanup=None):
        self.prev = None
        self.next_key = _null_key
        self.key = key
        self.value = value
        self.cleanup = cleanup
        # TODO: We could compute this 'on-the-fly' like we used to, and remove
        #       one pointer from this object, we just need to decide if it
        #       actually costs us much of anything in normal usage
        self.size = None

    def __repr__(self):
        if self.prev is None:
            prev_key = None
        else:
            prev_key = self.prev.key
        return '%s(%r n:%r p:%r)' % (self.__class__.__name__, self.key,
                                     self.next_key, prev_key)

    def run_cleanup(self):
        if self.cleanup is not None:
            self.cleanup(self.key, self.value)
        self.cleanup = None
        # Just make sure to break any refcycles, etc
        self.value = None


class LRUCache(object):
    """A class which manages a cache of entries, removing unused ones."""

    def __init__(self, max_cache=100, after_cleanup_count=None):
        self._cache = {}
        # The "HEAD" of the lru linked list
        self._most_recently_used = None
        # The "TAIL" of the lru linked list
        self._least_recently_used = None
        self._update_max_cache(max_cache, after_cleanup_count)

    def __contains__(self, key):
        return key in self._cache

    def __getitem__(self, key):
        cache = self._cache
        node = cache[key]
        # Inlined from _record_access to decrease the overhead of __getitem__
        # We also have more knowledge about structure if __getitem__ is
        # succeeding, then we know that self._most_recently_used must not be
        # None, etc.
        mru = self._most_recently_used
        if node is mru:
            # Nothing to do, this node is already at the head of the queue
            return node.value
        # Remove this node from the old location
        node_prev = node.prev
        next_key = node.next_key
        # benchmarking shows that the lookup of _null_key in globals is faster
        # than the attribute lookup for (node is self._least_recently_used)
        if next_key is _null_key:
            # 'node' is the _least_recently_used, because it doesn't have a
            # 'next' item. So move the current lru to the previous node.
            self._least_recently_used = node_prev
        else:
            node_next = cache[next_key]
            node_next.prev = node_prev
        node_prev.next_key = next_key
        # Insert this node at the front of the list
        node.next_key = mru.key
        mru.prev = node
        self._most_recently_used = node
        node.prev = None
        return node.value

    def __len__(self):
        return len(self._cache)

    def _walk_lru(self):
        """Walk the LRU list, only meant to be used in tests."""
        node = self._most_recently_used
        if node is not None:
            if node.prev is not None:
                raise AssertionError('the _most_recently_used entry is not'
                                     ' supposed to have a previous entry'
                                     ' %s' % (node,))
        while node is not None:
            if node.next_key is _null_key:
                if node is not self._least_recently_used:
                    raise AssertionError('only the last node should have'
                                         ' no next value: %s' % (node,))
                node_next = None
            else:
                node_next = self._cache[node.next_key]
                if node_next.prev is not node:
                    raise AssertionError('inconsistency found, node.next.prev'
                                         ' != node: %s' % (node,))
            if node.prev is None:
                if node is not self._most_recently_used:
                    raise AssertionError('only the _most_recently_used should'
                                         ' not have a previous node: %s'
                                         % (node,))
            else:
                if node.prev.next_key != node.key:
                    raise AssertionError('inconsistency found, node.prev.next'
                                         ' != node: %s' % (node,))
            yield node
            node = node_next

    def add(self, key, value, cleanup=None):
        """Add a new value to the cache.

        Also, if the entry is ever removed from the cache, call
        cleanup(key, value).

        :param key: The key to store it under
        :param value: The object to store
        :param cleanup: None or a function taking (key, value) to indicate
                        'value' should be cleaned up.
        """
        if key is _null_key:
            raise ValueError('cannot use _null_key as a key')
        if key in self._cache:
            node = self._cache[key]
            node.run_cleanup()
            node.value = value
            node.cleanup = cleanup
        else:
            node = _LRUNode(key, value, cleanup=cleanup)
            self._cache[key] = node
        self._record_access(node)

        if len(self._cache) > self._max_cache:
            # Trigger the cleanup
            self.cleanup()

    def cache_size(self):
        """Get the number of entries we will cache."""
        return self._max_cache

    def get(self, key, default=None):
        node = self._cache.get(key, None)
        if node is None:
            return default
        self._record_access(node)
        return node.value

    def keys(self):
        """Get the list of keys currently cached.

        Note that values returned here may not be available by the time you
        request them later. This is simply meant as a peak into the current
        state.

        :return: An unordered list of keys that are currently cached.
        """
        return self._cache.keys()

    def items(self):
        """Get the key:value pairs as a dict."""
        return dict((k, n.value) for k, n in self._cache.iteritems())

    def cleanup(self):
        """Clear the cache until it shrinks to the requested size.

        This does not completely wipe the cache, just makes sure it is under
        the after_cleanup_count.
        """
        # Make sure the cache is shrunk to the correct size
        while len(self._cache) > self._after_cleanup_count:
            self._remove_lru()

    def __setitem__(self, key, value):
        """Add a value to the cache, there will be no cleanup function."""
        self.add(key, value, cleanup=None)

    def _record_access(self, node):
        """Record that key was accessed."""
        # Move 'node' to the front of the queue
        if self._most_recently_used is None:
            self._most_recently_used = node
            self._least_recently_used = node
            return
        elif node is self._most_recently_used:
            # Nothing to do, this node is already at the head of the queue
            return
        # We've taken care of the tail pointer, remove the node, and insert it
        # at the front
        # REMOVE
        if node is self._least_recently_used:
            self._least_recently_used = node.prev
        if node.prev is not None:
            node.prev.next_key = node.next_key
        if node.next_key is not _null_key:
            node_next = self._cache[node.next_key]
            node_next.prev = node.prev
        # INSERT
        node.next_key = self._most_recently_used.key
        self._most_recently_used.prev = node
        self._most_recently_used = node
        node.prev = None

    def _remove_node(self, node):
        if node is self._least_recently_used:
            self._least_recently_used = node.prev
        self._cache.pop(node.key)
        # If we have removed all entries, remove the head pointer as well
        if self._least_recently_used is None:
            self._most_recently_used = None
        node.run_cleanup()
        # Now remove this node from the linked list
        if node.prev is not None:
            node.prev.next_key = node.next_key
        if node.next_key is not _null_key:
            node_next = self._cache[node.next_key]
            node_next.prev = node.prev
        # And remove this node's pointers
        node.prev = None
        node.next_key = _null_key

    def _remove_lru(self):
        """Remove one entry from the lru, and handle consequences.

        If there are no more references to the lru, then this entry should be
        removed from the cache.
        """
        self._remove_node(self._least_recently_used)

    def clear(self):
        """Clear out all of the cache."""
        # Clean up in LRU order
        while self._cache:
            self._remove_lru()

    def resize(self, max_cache, after_cleanup_count=None):
        """Change the number of entries that will be cached."""
        self._update_max_cache(max_cache,
                               after_cleanup_count=after_cleanup_count)

    def _update_max_cache(self, max_cache, after_cleanup_count=None):
        self._max_cache = max_cache
        if after_cleanup_count is None:
            self._after_cleanup_count = self._max_cache * 8 / 10
        else:
            self._after_cleanup_count = min(after_cleanup_count,
                                            self._max_cache)
        self.cleanup()


class LRUSizeCache(LRUCache):
    """An LRUCache that removes things based on the size of the values.

    This differs in that it doesn't care how many actual items there are,
    it just restricts the cache to be cleaned up after so much data is stored.

    The size of items added will be computed using compute_size(value), which
    defaults to len() if not supplied.
    """

    def __init__(self, max_size=1024*1024, after_cleanup_size=None,
                 compute_size=None):
        """Create a new LRUSizeCache.

        :param max_size: The max number of bytes to store before we start
            clearing out entries.
        :param after_cleanup_size: After cleaning up, shrink everything to this
            size.
        :param compute_size: A function to compute the size of the values. We
            use a function here, so that you can pass 'len' if you are just
            using simple strings, or a more complex function if you are using
            something like a list of strings, or even a custom object.
            The function should take the form "compute_size(value) => integer".
            If not supplied, it defaults to 'len()'
        """
        self._value_size = 0
        self._compute_size = compute_size
        if compute_size is None:
            self._compute_size = len
        self._update_max_size(max_size, after_cleanup_size=after_cleanup_size)
        LRUCache.__init__(self, max_cache=max(int(max_size/512), 1))

    def add(self, key, value, cleanup=None):
        """Add a new value to the cache.

        Also, if the entry is ever removed from the cache, call
        cleanup(key, value).

        :param key: The key to store it under
        :param value: The object to store
        :param cleanup: None or a function taking (key, value) to indicate
                        'value' should be cleaned up.
        """
        if key is _null_key:
            raise ValueError('cannot use _null_key as a key')
        node = self._cache.get(key, None)
        value_len = self._compute_size(value)
        if value_len >= self._after_cleanup_size:
            # The new value is 'too big to fit', as it would fill up/overflow
            # the cache all by itself
            if node is not None:
                # We won't be replacing the old node, so just remove it
                self._remove_node(node)
            if cleanup is not None:
                cleanup(key, value)
            return
        if node is None:
            node = _LRUNode(key, value, cleanup=cleanup)
            self._cache[key] = node
        else:
            self._value_size -= node.size
        node.size = value_len
        self._value_size += value_len
        self._record_access(node)

        if self._value_size > self._max_size:
            # Time to cleanup
            self.cleanup()

    def cleanup(self):
        """Clear the cache until it shrinks to the requested size.

        This does not completely wipe the cache, just makes sure it is under
        the after_cleanup_size.
        """
        # Make sure the cache is shrunk to the correct size
        while self._value_size > self._after_cleanup_size:
            self._remove_lru()

    def _remove_node(self, node):
        self._value_size -= node.size
        LRUCache._remove_node(self, node)

    def resize(self, max_size, after_cleanup_size=None):
        """Change the number of bytes that will be cached."""
        self._update_max_size(max_size, after_cleanup_size=after_cleanup_size)
        max_cache = max(int(max_size/512), 1)
        self._update_max_cache(max_cache)

    def _update_max_size(self, max_size, after_cleanup_size=None):
        self._max_size = max_size
        if after_cleanup_size is None:
            self._after_cleanup_size = self._max_size * 8 / 10
        else:
            self._after_cleanup_size = min(after_cleanup_size, self._max_size)

########NEW FILE########
__FILENAME__ = objects
# objects.py -- Access to base git objects
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Access to base git objects."""

import binascii
from cStringIO import (
    StringIO,
    )
import os
import posixpath
import stat
import warnings
import zlib

from dulwich.errors import (
    ChecksumMismatch,
    NotBlobError,
    NotCommitError,
    NotTagError,
    NotTreeError,
    ObjectFormatException,
    )
from dulwich.file import GitFile
from dulwich._compat import (
    make_sha,
    namedtuple,
    )

ZERO_SHA = "0" * 40

# Header fields for commits
_TREE_HEADER = "tree"
_PARENT_HEADER = "parent"
_AUTHOR_HEADER = "author"
_COMMITTER_HEADER = "committer"
_ENCODING_HEADER = "encoding"
_MERGETAG_HEADER = "mergetag"

# Header fields for objects
_OBJECT_HEADER = "object"
_TYPE_HEADER = "type"
_TAG_HEADER = "tag"
_TAGGER_HEADER = "tagger"


S_IFGITLINK = 0160000

def S_ISGITLINK(m):
    """Check if a mode indicates a submodule.

    :param m: Mode to check
    :return: a ``boolean``
    """
    return (stat.S_IFMT(m) == S_IFGITLINK)


def _decompress(string):
    dcomp = zlib.decompressobj()
    dcomped = dcomp.decompress(string)
    dcomped += dcomp.flush()
    return dcomped


def sha_to_hex(sha):
    """Takes a string and returns the hex of the sha within"""
    hexsha = binascii.hexlify(sha)
    assert len(hexsha) == 40, "Incorrect length of sha1 string: %d" % hexsha
    return hexsha


def hex_to_sha(hex):
    """Takes a hex sha and returns a binary sha"""
    assert len(hex) == 40, "Incorrent length of hexsha: %s" % hex
    try:
        return binascii.unhexlify(hex)
    except TypeError, exc:
        if not isinstance(hex, str):
            raise
        raise ValueError(exc.message)


def hex_to_filename(path, hex):
    """Takes a hex sha and returns its filename relative to the given path."""
    dir = hex[:2]
    file = hex[2:]
    # Check from object dir
    return os.path.join(path, dir, file)


def filename_to_hex(filename):
    """Takes an object filename and returns its corresponding hex sha."""
    # grab the last (up to) two path components
    names = filename.rsplit(os.path.sep, 2)[-2:]
    errmsg = "Invalid object filename: %s" % filename
    assert len(names) == 2, errmsg
    base, rest = names
    assert len(base) == 2 and len(rest) == 38, errmsg
    hex = base + rest
    hex_to_sha(hex)
    return hex


def object_header(num_type, length):
    """Return an object header for the given numeric type and text length."""
    return "%s %d\0" % (object_class(num_type).type_name, length)


def serializable_property(name, docstring=None):
    """A property that helps tracking whether serialization is necessary.
    """
    def set(obj, value):
        obj._ensure_parsed()
        setattr(obj, "_"+name, value)
        obj._needs_serialization = True
    def get(obj):
        obj._ensure_parsed()
        return getattr(obj, "_"+name)
    return property(get, set, doc=docstring)


def object_class(type):
    """Get the object class corresponding to the given type.

    :param type: Either a type name string or a numeric type.
    :return: The ShaFile subclass corresponding to the given type, or None if
        type is not a valid type name/number.
    """
    return _TYPE_MAP.get(type, None)


def check_hexsha(hex, error_msg):
    """Check if a string is a valid hex sha string.

    :param hex: Hex string to check
    :param error_msg: Error message to use in exception
    :raise ObjectFormatException: Raised when the string is not valid
    """
    try:
        hex_to_sha(hex)
    except (TypeError, AssertionError, ValueError):
        raise ObjectFormatException("%s %s" % (error_msg, hex))


def check_identity(identity, error_msg):
    """Check if the specified identity is valid.

    This will raise an exception if the identity is not valid.

    :param identity: Identity string
    :param error_msg: Error message to use in exception
    """
    email_start = identity.find("<")
    email_end = identity.find(">")
    if (email_start < 0 or email_end < 0 or email_end <= email_start
        or identity.find("<", email_start + 1) >= 0
        or identity.find(">", email_end + 1) >= 0
        or not identity.endswith(">")):
        raise ObjectFormatException(error_msg)


class FixedSha(object):
    """SHA object that behaves like hashlib's but is given a fixed value."""

    __slots__ = ('_hexsha', '_sha')

    def __init__(self, hexsha):
        self._hexsha = hexsha
        self._sha = hex_to_sha(hexsha)

    def digest(self):
        """Return the raw SHA digest."""
        return self._sha

    def hexdigest(self):
        """Return the hex SHA digest."""
        return self._hexsha


class ShaFile(object):
    """A git SHA file."""

    __slots__ = ('_needs_parsing', '_chunked_text', '_file', '_path',
                 '_sha', '_needs_serialization', '_magic')

    @staticmethod
    def _parse_legacy_object_header(magic, f):
        """Parse a legacy object, creating it but not reading the file."""
        bufsize = 1024
        decomp = zlib.decompressobj()
        header = decomp.decompress(magic)
        start = 0
        end = -1
        while end < 0:
            extra = f.read(bufsize)
            header += decomp.decompress(extra)
            magic += extra
            end = header.find("\0", start)
            start = len(header)
        header = header[:end]
        type_name, size = header.split(" ", 1)
        size = int(size)  # sanity check
        obj_class = object_class(type_name)
        if not obj_class:
            raise ObjectFormatException("Not a known type: %s" % type_name)
        ret = obj_class()
        ret._magic = magic
        return ret

    def _parse_legacy_object(self, map):
        """Parse a legacy object, setting the raw string."""
        text = _decompress(map)
        header_end = text.find('\0')
        if header_end < 0:
            raise ObjectFormatException("Invalid object header, no \\0")
        self.set_raw_string(text[header_end+1:])

    def as_legacy_object_chunks(self):
        """Return chunks representing the object in the experimental format.

        :return: List of strings
        """
        compobj = zlib.compressobj()
        yield compobj.compress(self._header())
        for chunk in self.as_raw_chunks():
            yield compobj.compress(chunk)
        yield compobj.flush()

    def as_legacy_object(self):
        """Return string representing the object in the experimental format.
        """
        return "".join(self.as_legacy_object_chunks())

    def as_raw_chunks(self):
        """Return chunks with serialization of the object.

        :return: List of strings, not necessarily one per line
        """
        if self._needs_parsing:
            self._ensure_parsed()
        elif self._needs_serialization:
            self._chunked_text = self._serialize()
        return self._chunked_text

    def as_raw_string(self):
        """Return raw string with serialization of the object.

        :return: String object
        """
        return "".join(self.as_raw_chunks())

    def __str__(self):
        """Return raw string serialization of this object."""
        return self.as_raw_string()

    def __hash__(self):
        """Return unique hash for this object."""
        return hash(self.id)

    def as_pretty_string(self):
        """Return a string representing this object, fit for display."""
        return self.as_raw_string()

    def _ensure_parsed(self):
        if self._needs_parsing:
            if not self._chunked_text:
                if self._file is not None:
                    self._parse_file(self._file)
                    self._file = None
                elif self._path is not None:
                    self._parse_path()
                else:
                    raise AssertionError(
                        "ShaFile needs either text or filename")
            self._deserialize(self._chunked_text)
            self._needs_parsing = False

    def set_raw_string(self, text):
        """Set the contents of this object from a serialized string."""
        if type(text) != str:
            raise TypeError(text)
        self.set_raw_chunks([text])

    def set_raw_chunks(self, chunks):
        """Set the contents of this object from a list of chunks."""
        self._chunked_text = chunks
        self._deserialize(chunks)
        self._sha = None
        self._needs_parsing = False
        self._needs_serialization = False

    @staticmethod
    def _parse_object_header(magic, f):
        """Parse a new style object, creating it but not reading the file."""
        num_type = (ord(magic[0]) >> 4) & 7
        obj_class = object_class(num_type)
        if not obj_class:
            raise ObjectFormatException("Not a known type %d" % num_type)
        ret = obj_class()
        ret._magic = magic
        return ret

    def _parse_object(self, map):
        """Parse a new style object, setting self._text."""
        # skip type and size; type must have already been determined, and
        # we trust zlib to fail if it's otherwise corrupted
        byte = ord(map[0])
        used = 1
        while (byte & 0x80) != 0:
            byte = ord(map[used])
            used += 1
        raw = map[used:]
        self.set_raw_string(_decompress(raw))

    @classmethod
    def _is_legacy_object(cls, magic):
        b0, b1 = map(ord, magic)
        word = (b0 << 8) + b1
        return (b0 & 0x8F) == 0x08 and (word % 31) == 0

    @classmethod
    def _parse_file_header(cls, f):
        magic = f.read(2)
        if cls._is_legacy_object(magic):
            return cls._parse_legacy_object_header(magic, f)
        else:
            return cls._parse_object_header(magic, f)

    def __init__(self):
        """Don't call this directly"""
        self._sha = None
        self._path = None
        self._file = None
        self._magic = None
        self._chunked_text = []
        self._needs_parsing = False
        self._needs_serialization = True

    def _deserialize(self, chunks):
        raise NotImplementedError(self._deserialize)

    def _serialize(self):
        raise NotImplementedError(self._serialize)

    def _parse_path(self):
        f = GitFile(self._path, 'rb')
        try:
            self._parse_file(f)
        finally:
            f.close()

    def _parse_file(self, f):
        magic = self._magic
        if magic is None:
            magic = f.read(2)
        map = magic + f.read()
        if self._is_legacy_object(magic[:2]):
            self._parse_legacy_object(map)
        else:
            self._parse_object(map)

    @classmethod
    def from_path(cls, path):
        """Open a SHA file from disk."""
        f = GitFile(path, 'rb')
        try:
            obj = cls.from_file(f)
            obj._path = path
            obj._sha = FixedSha(filename_to_hex(path))
            obj._file = None
            obj._magic = None
            return obj
        finally:
            f.close()

    @classmethod
    def from_file(cls, f):
        """Get the contents of a SHA file on disk."""
        try:
            obj = cls._parse_file_header(f)
            obj._sha = None
            obj._needs_parsing = True
            obj._needs_serialization = True
            obj._file = f
            return obj
        except (IndexError, ValueError), e:
            raise ObjectFormatException("invalid object header")

    @staticmethod
    def from_raw_string(type_num, string):
        """Creates an object of the indicated type from the raw string given.

        :param type_num: The numeric type of the object.
        :param string: The raw uncompressed contents.
        """
        obj = object_class(type_num)()
        obj.set_raw_string(string)
        return obj

    @staticmethod
    def from_raw_chunks(type_num, chunks):
        """Creates an object of the indicated type from the raw chunks given.

        :param type_num: The numeric type of the object.
        :param chunks: An iterable of the raw uncompressed contents.
        """
        obj = object_class(type_num)()
        obj.set_raw_chunks(chunks)
        return obj

    @classmethod
    def from_string(cls, string):
        """Create a ShaFile from a string."""
        obj = cls()
        obj.set_raw_string(string)
        return obj

    def _check_has_member(self, member, error_msg):
        """Check that the object has a given member variable.

        :param member: the member variable to check for
        :param error_msg: the message for an error if the member is missing
        :raise ObjectFormatException: with the given error_msg if member is
            missing or is None
        """
        if getattr(self, member, None) is None:
            raise ObjectFormatException(error_msg)

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        :raise ChecksumMismatch: if the object was created with a SHA that does
            not match its contents
        """
        # TODO: if we find that error-checking during object parsing is a
        # performance bottleneck, those checks should be moved to the class's
        # check() method during optimization so we can still check the object
        # when necessary.
        old_sha = self.id
        try:
            self._deserialize(self.as_raw_chunks())
            self._sha = None
            new_sha = self.id
        except Exception, e:
            raise ObjectFormatException(e)
        if old_sha != new_sha:
            raise ChecksumMismatch(new_sha, old_sha)

    def _header(self):
        return object_header(self.type, self.raw_length())

    def raw_length(self):
        """Returns the length of the raw string of this object."""
        ret = 0
        for chunk in self.as_raw_chunks():
            ret += len(chunk)
        return ret

    def _make_sha(self):
        ret = make_sha()
        ret.update(self._header())
        for chunk in self.as_raw_chunks():
            ret.update(chunk)
        return ret

    def sha(self):
        """The SHA1 object that is the name of this object."""
        if self._sha is None or self._needs_serialization:
            # this is a local because as_raw_chunks() overwrites self._sha
            new_sha = make_sha()
            new_sha.update(self._header())
            for chunk in self.as_raw_chunks():
                new_sha.update(chunk)
            self._sha = new_sha
        return self._sha

    @property
    def id(self):
        """The hex SHA of this object."""
        return self.sha().hexdigest()

    def get_type(self):
        """Return the type number for this object class."""
        return self.type_num

    def set_type(self, type):
        """Set the type number for this object class."""
        self.type_num = type

    # DEPRECATED: use type_num or type_name as needed.
    type = property(get_type, set_type)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.id)

    def __ne__(self, other):
        return not isinstance(other, ShaFile) or self.id != other.id

    def __eq__(self, other):
        """Return True if the SHAs of the two objects match.

        It doesn't make sense to talk about an order on ShaFiles, so we don't
        override the rich comparison methods (__le__, etc.).
        """
        return isinstance(other, ShaFile) and self.id == other.id


class Blob(ShaFile):
    """A Git Blob object."""

    __slots__ = ()

    type_name = 'blob'
    type_num = 3

    def __init__(self):
        super(Blob, self).__init__()
        self._chunked_text = []
        self._needs_parsing = False
        self._needs_serialization = False

    def _get_data(self):
        return self.as_raw_string()

    def _set_data(self, data):
        self.set_raw_string(data)

    data = property(_get_data, _set_data,
                    "The text contained within the blob object.")

    def _get_chunked(self):
        self._ensure_parsed()
        return self._chunked_text

    def _set_chunked(self, chunks):
        self._chunked_text = chunks

    def _serialize(self):
        if not self._chunked_text:
            self._ensure_parsed()
        self._needs_serialization = False
        return self._chunked_text

    def _deserialize(self, chunks):
        self._chunked_text = chunks

    chunked = property(_get_chunked, _set_chunked,
        "The text within the blob object, as chunks (not necessarily lines).")

    @classmethod
    def from_path(cls, path):
        blob = ShaFile.from_path(path)
        if not isinstance(blob, cls):
            raise NotBlobError(path)
        return blob

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        """
        super(Blob, self).check()


def _parse_tag_or_commit(text):
    """Parse tag or commit text.

    :param text: the raw text of the tag or commit object.
    :return: iterator of tuples of (field, value), one per header line, in the
        order read from the text, possibly including duplicates. Includes a
        field named None for the freeform tag/commit text.
    """
    f = StringIO(text)
    k = None
    v = ""
    for l in f:
        if l.startswith(" "):
            v += l[1:]
        else:
            if k is not None:
                yield (k, v.rstrip("\n"))
            if l == "\n":
                # Empty line indicates end of headers
                break
            (k, v) = l.split(" ", 1)
    yield (None, f.read())
    f.close()


def parse_tag(text):
    """Parse a tag object."""
    return _parse_tag_or_commit(text)


class Tag(ShaFile):
    """A Git Tag object."""

    type_name = 'tag'
    type_num = 4

    __slots__ = ('_tag_timezone_neg_utc', '_name', '_object_sha',
                 '_object_class', '_tag_time', '_tag_timezone',
                 '_tagger', '_message')

    def __init__(self):
        super(Tag, self).__init__()
        self._tag_timezone_neg_utc = False

    @classmethod
    def from_path(cls, filename):
        tag = ShaFile.from_path(filename)
        if not isinstance(tag, cls):
            raise NotTagError(filename)
        return tag

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        """
        super(Tag, self).check()
        self._check_has_member("_object_sha", "missing object sha")
        self._check_has_member("_object_class", "missing object type")
        self._check_has_member("_name", "missing tag name")

        if not self._name:
            raise ObjectFormatException("empty tag name")

        check_hexsha(self._object_sha, "invalid object sha")

        if getattr(self, "_tagger", None):
            check_identity(self._tagger, "invalid tagger")

        last = None
        for field, _ in parse_tag("".join(self._chunked_text)):
            if field == _OBJECT_HEADER and last is not None:
                raise ObjectFormatException("unexpected object")
            elif field == _TYPE_HEADER and last != _OBJECT_HEADER:
                raise ObjectFormatException("unexpected type")
            elif field == _TAG_HEADER and last != _TYPE_HEADER:
                raise ObjectFormatException("unexpected tag name")
            elif field == _TAGGER_HEADER and last != _TAG_HEADER:
                raise ObjectFormatException("unexpected tagger")
            last = field

    def _serialize(self):
        chunks = []
        chunks.append("%s %s\n" % (_OBJECT_HEADER, self._object_sha))
        chunks.append("%s %s\n" % (_TYPE_HEADER, self._object_class.type_name))
        chunks.append("%s %s\n" % (_TAG_HEADER, self._name))
        if self._tagger:
            if self._tag_time is None:
                chunks.append("%s %s\n" % (_TAGGER_HEADER, self._tagger))
            else:
                chunks.append("%s %s %d %s\n" % (
                  _TAGGER_HEADER, self._tagger, self._tag_time,
                  format_timezone(self._tag_timezone,
                    self._tag_timezone_neg_utc)))
        chunks.append("\n") # To close headers
        chunks.append(self._message)
        return chunks

    def _deserialize(self, chunks):
        """Grab the metadata attached to the tag"""
        self._tagger = None
        for field, value in parse_tag("".join(chunks)):
            if field == _OBJECT_HEADER:
                self._object_sha = value
            elif field == _TYPE_HEADER:
                obj_class = object_class(value)
                if not obj_class:
                    raise ObjectFormatException("Not a known type: %s" % value)
                self._object_class = obj_class
            elif field == _TAG_HEADER:
                self._name = value
            elif field == _TAGGER_HEADER:
                try:
                    sep = value.index("> ")
                except ValueError:
                    self._tagger = value
                    self._tag_time = None
                    self._tag_timezone = None
                    self._tag_timezone_neg_utc = False
                else:
                    self._tagger = value[0:sep+1]
                    try:
                        (timetext, timezonetext) = value[sep+2:].rsplit(" ", 1)
                        self._tag_time = int(timetext)
                        self._tag_timezone, self._tag_timezone_neg_utc = \
                                parse_timezone(timezonetext)
                    except ValueError, e:
                        raise ObjectFormatException(e)
            elif field is None:
                self._message = value
            else:
                raise ObjectFormatException("Unknown field %s" % field)

    def _get_object(self):
        """Get the object pointed to by this tag.

        :return: tuple of (object class, sha).
        """
        self._ensure_parsed()
        return (self._object_class, self._object_sha)

    def _set_object(self, value):
        self._ensure_parsed()
        (self._object_class, self._object_sha) = value
        self._needs_serialization = True

    object = property(_get_object, _set_object)

    name = serializable_property("name", "The name of this tag")
    tagger = serializable_property("tagger",
        "Returns the name of the person who created this tag")
    tag_time = serializable_property("tag_time",
        "The creation timestamp of the tag.  As the number of seconds since the epoch")
    tag_timezone = serializable_property("tag_timezone",
        "The timezone that tag_time is in.")
    message = serializable_property("message", "The message attached to this tag")


class TreeEntry(namedtuple('TreeEntry', ['path', 'mode', 'sha'])):
    """Named tuple encapsulating a single tree entry."""

    def in_path(self, path):
        """Return a copy of this entry with the given path prepended."""
        if type(self.path) != str:
            raise TypeError
        return TreeEntry(posixpath.join(path, self.path), self.mode, self.sha)


def parse_tree(text, strict=False):
    """Parse a tree text.

    :param text: Serialized text to parse
    :return: iterator of tuples of (name, mode, sha)
    :raise ObjectFormatException: if the object was malformed in some way
    """
    count = 0
    l = len(text)
    while count < l:
        mode_end = text.index(' ', count)
        mode_text = text[count:mode_end]
        if strict and mode_text.startswith('0'):
            raise ObjectFormatException("Invalid mode '%s'" % mode_text)
        try:
            mode = int(mode_text, 8)
        except ValueError:
            raise ObjectFormatException("Invalid mode '%s'" % mode_text)
        name_end = text.index('\0', mode_end)
        name = text[mode_end+1:name_end]
        count = name_end+21
        sha = text[name_end+1:count]
        if len(sha) != 20:
            raise ObjectFormatException("Sha has invalid length")
        hexsha = sha_to_hex(sha)
        yield (name, mode, hexsha)


def serialize_tree(items):
    """Serialize the items in a tree to a text.

    :param items: Sorted iterable over (name, mode, sha) tuples
    :return: Serialized tree text as chunks
    """
    for name, mode, hexsha in items:
        yield "%04o %s\0%s" % (mode, name, hex_to_sha(hexsha))


def sorted_tree_items(entries, name_order):
    """Iterate over a tree entries dictionary.

    :param name_order: If True, iterate entries in order of their name. If
        False, iterate entries in tree order, that is, treat subtree entries as
        having '/' appended.
    :param entries: Dictionary mapping names to (mode, sha) tuples
    :return: Iterator over (name, mode, hexsha)
    """
    cmp_func = name_order and cmp_entry_name_order or cmp_entry
    for name, entry in sorted(entries.iteritems(), cmp=cmp_func):
        mode, hexsha = entry
        # Stricter type checks than normal to mirror checks in the C version.
        if not isinstance(mode, int) and not isinstance(mode, long):
            raise TypeError('Expected integer/long for mode, got %r' % mode)
        mode = int(mode)
        if not isinstance(hexsha, str):
            raise TypeError('Expected a string for SHA, got %r' % hexsha)
        yield TreeEntry(name, mode, hexsha)


def cmp_entry((name1, value1), (name2, value2)):
    """Compare two tree entries in tree order."""
    if stat.S_ISDIR(value1[0]):
        name1 += "/"
    if stat.S_ISDIR(value2[0]):
        name2 += "/"
    return cmp(name1, name2)


def cmp_entry_name_order(entry1, entry2):
    """Compare two tree entries in name order."""
    return cmp(entry1[0], entry2[0])


class Tree(ShaFile):
    """A Git tree object"""

    type_name = 'tree'
    type_num = 2

    __slots__ = ('_entries')

    def __init__(self):
        super(Tree, self).__init__()
        self._entries = {}

    @classmethod
    def from_path(cls, filename):
        tree = ShaFile.from_path(filename)
        if not isinstance(tree, cls):
            raise NotTreeError(filename)
        return tree

    def __contains__(self, name):
        self._ensure_parsed()
        return name in self._entries

    def __getitem__(self, name):
        self._ensure_parsed()
        return self._entries[name]

    def __setitem__(self, name, value):
        """Set a tree entry by name.

        :param name: The name of the entry, as a string.
        :param value: A tuple of (mode, hexsha), where mode is the mode of the
            entry as an integral type and hexsha is the hex SHA of the entry as
            a string.
        """
        mode, hexsha = value
        self._ensure_parsed()
        self._entries[name] = (mode, hexsha)
        self._needs_serialization = True

    def __delitem__(self, name):
        self._ensure_parsed()
        del self._entries[name]
        self._needs_serialization = True

    def __len__(self):
        self._ensure_parsed()
        return len(self._entries)

    def __iter__(self):
        self._ensure_parsed()
        return iter(self._entries)

    def add(self, name, mode, hexsha):
        """Add an entry to the tree.

        :param mode: The mode of the entry as an integral type. Not all
            possible modes are supported by git; see check() for details.
        :param name: The name of the entry, as a string.
        :param hexsha: The hex SHA of the entry as a string.
        """
        if type(name) is int and type(mode) is str:
            (name, mode) = (mode, name)
            warnings.warn("Please use Tree.add(name, mode, hexsha)",
                category=DeprecationWarning, stacklevel=2)
        self._ensure_parsed()
        self._entries[name] = mode, hexsha
        self._needs_serialization = True

    def entries(self):
        """Return a list of tuples describing the tree entries.

        :note: The order of the tuples that are returned is different from that
            returned by the items and iteritems methods. This function will be
            deprecated in the future.
        """
        warnings.warn("Tree.entries() is deprecated. Use Tree.items() or"
            " Tree.iteritems() instead.", category=DeprecationWarning,
            stacklevel=2)
        self._ensure_parsed()
        # The order of this is different from iteritems() for historical
        # reasons
        return [
            (mode, name, hexsha) for (name, mode, hexsha) in self.iteritems()]

    def iteritems(self, name_order=False):
        """Iterate over entries.

        :param name_order: If True, iterate in name order instead of tree order.
        :return: Iterator over (name, mode, sha) tuples
        """
        self._ensure_parsed()
        return sorted_tree_items(self._entries, name_order)

    def items(self):
        """Return the sorted entries in this tree.

        :return: List with (name, mode, sha) tuples
        """
        return list(self.iteritems())

    def _deserialize(self, chunks):
        """Grab the entries in the tree"""
        try:
            parsed_entries = parse_tree("".join(chunks))
        except ValueError, e:
            raise ObjectFormatException(e)
        # TODO: list comprehension is for efficiency in the common (small) case;
        # if memory efficiency in the large case is a concern, use a genexp.
        self._entries = dict([(n, (m, s)) for n, m, s in parsed_entries])

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        """
        super(Tree, self).check()
        last = None
        allowed_modes = (stat.S_IFREG | 0755, stat.S_IFREG | 0644,
                         stat.S_IFLNK, stat.S_IFDIR, S_IFGITLINK,
                         # TODO: optionally exclude as in git fsck --strict
                         stat.S_IFREG | 0664)
        for name, mode, sha in parse_tree(''.join(self._chunked_text),
                                          True):
            check_hexsha(sha, 'invalid sha %s' % sha)
            if '/' in name or name in ('', '.', '..'):
                raise ObjectFormatException('invalid name %s' % name)

            if mode not in allowed_modes:
                raise ObjectFormatException('invalid mode %06o' % mode)

            entry = (name, (mode, sha))
            if last:
                if cmp_entry(last, entry) > 0:
                    raise ObjectFormatException('entries not sorted')
                if name == last[0]:
                    raise ObjectFormatException('duplicate entry %s' % name)
            last = entry

    def _serialize(self):
        return list(serialize_tree(self.iteritems()))

    def as_pretty_string(self):
        text = []
        for name, mode, hexsha in self.iteritems():
            if mode & stat.S_IFDIR:
                kind = "tree"
            else:
                kind = "blob"
            text.append("%04o %s %s\t%s\n" % (mode, kind, hexsha, name))
        return "".join(text)

    def lookup_path(self, lookup_obj, path):
        """Look up an object in a Git tree.

        :param lookup_obj: Callback for retrieving object by SHA1
        :param path: Path to lookup
        :return: A tuple of (mode, SHA) of the resulting path.
        """
        parts = path.split('/')
        sha = self.id
        mode = None
        for p in parts:
            if not p:
                continue
            obj = lookup_obj(sha)
            if not isinstance(obj, Tree):
                raise NotTreeError(sha)
            mode, sha = obj[p]
        return mode, sha


def parse_timezone(text):
    """Parse a timezone text fragment (e.g. '+0100').

    :param text: Text to parse.
    :return: Tuple with timezone as seconds difference to UTC
        and a boolean indicating whether this was a UTC timezone
        prefixed with a negative sign (-0000).
    """
    # cgit parses the first character as the sign, and the rest
    #  as an integer (using strtol), which could also be negative.
    #  We do the same for compatibility. See #697828.
    if not text[0] in '+-':
        raise ValueError("Timezone must start with + or - (%(text)s)" % vars())
    sign = text[0]
    offset = int(text[1:])
    if sign == '-':
        offset = -offset
    unnecessary_negative_timezone = (offset >= 0 and sign == '-')
    signum = (offset < 0) and -1 or 1
    offset = abs(offset)
    hours = int(offset / 100)
    minutes = (offset % 100)
    return (signum * (hours * 3600 + minutes * 60),
            unnecessary_negative_timezone)


def format_timezone(offset, unnecessary_negative_timezone=False):
    """Format a timezone for Git serialization.

    :param offset: Timezone offset as seconds difference to UTC
    :param unnecessary_negative_timezone: Whether to use a minus sign for
        UTC or positive timezones (-0000 and --700 rather than +0000 / +0700).
    """
    if offset % 60 != 0:
        raise ValueError("Unable to handle non-minute offset.")
    if offset < 0 or unnecessary_negative_timezone:
        sign = '-'
        offset = -offset
    else:
        sign = '+'
    return '%c%02d%02d' % (sign, offset / 3600, (offset / 60) % 60)


def parse_commit(text):
    return _parse_tag_or_commit(text)


class Commit(ShaFile):
    """A git commit object"""

    type_name = 'commit'
    type_num = 1

    __slots__ = ('_parents', '_encoding', '_extra', '_author_timezone_neg_utc',
                 '_commit_timezone_neg_utc', '_commit_time',
                 '_author_time', '_author_timezone', '_commit_timezone',
                 '_author', '_committer', '_parents', '_extra',
                 '_encoding', '_tree', '_message', '_mergetag')

    def __init__(self):
        super(Commit, self).__init__()
        self._parents = []
        self._encoding = None
        self._mergetag = []
        self._extra = []
        self._author_timezone_neg_utc = False
        self._commit_timezone_neg_utc = False

    @classmethod
    def from_path(cls, path):
        commit = ShaFile.from_path(path)
        if not isinstance(commit, cls):
            raise NotCommitError(path)
        return commit

    def _deserialize(self, chunks):
        self._parents = []
        self._extra = []
        self._author = None
        for field, value in parse_commit(''.join(chunks)):
            if field == _TREE_HEADER:
                self._tree = value
            elif field == _PARENT_HEADER:
                self._parents.append(value)
            elif field == _AUTHOR_HEADER:
                self._author, timetext, timezonetext = value.rsplit(" ", 2)
                self._author_time = int(timetext)
                self._author_timezone, self._author_timezone_neg_utc =\
                    parse_timezone(timezonetext)
            elif field == _COMMITTER_HEADER:
                self._committer, timetext, timezonetext = value.rsplit(" ", 2)
                self._commit_time = int(timetext)
                self._commit_timezone, self._commit_timezone_neg_utc =\
                    parse_timezone(timezonetext)
            elif field == _ENCODING_HEADER:
                self._encoding = value
            elif field is None:
                self._message = value
            elif field == _MERGETAG_HEADER:
                self._mergetag.append(Tag.from_string(value + "\n"))
            else:
                self._extra.append((field, value))

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        """
        super(Commit, self).check()
        self._check_has_member("_tree", "missing tree")
        self._check_has_member("_author", "missing author")
        self._check_has_member("_committer", "missing committer")
        # times are currently checked when set

        for parent in self._parents:
            check_hexsha(parent, "invalid parent sha")
        check_hexsha(self._tree, "invalid tree sha")

        check_identity(self._author, "invalid author")
        check_identity(self._committer, "invalid committer")

        last = None
        for field, _ in parse_commit("".join(self._chunked_text)):
            if field == _TREE_HEADER and last is not None:
                raise ObjectFormatException("unexpected tree")
            elif field == _PARENT_HEADER and last not in (_PARENT_HEADER,
                                                          _TREE_HEADER):
                raise ObjectFormatException("unexpected parent")
            elif field == _AUTHOR_HEADER and last not in (_TREE_HEADER,
                                                          _PARENT_HEADER):
                raise ObjectFormatException("unexpected author")
            elif field == _COMMITTER_HEADER and last != _AUTHOR_HEADER:
                raise ObjectFormatException("unexpected committer")
            elif field == _ENCODING_HEADER and last != _COMMITTER_HEADER:
                raise ObjectFormatException("unexpected encoding")
            last = field

        # TODO: optionally check for duplicate parents

    def _serialize(self):
        chunks = []
        chunks.append("%s %s\n" % (_TREE_HEADER, self._tree))
        for p in self._parents:
            chunks.append("%s %s\n" % (_PARENT_HEADER, p))
        chunks.append("%s %s %s %s\n" % (
          _AUTHOR_HEADER, self._author, str(self._author_time),
          format_timezone(self._author_timezone,
                          self._author_timezone_neg_utc)))
        chunks.append("%s %s %s %s\n" % (
          _COMMITTER_HEADER, self._committer, str(self._commit_time),
          format_timezone(self._commit_timezone,
                          self._commit_timezone_neg_utc)))
        if self.encoding:
            chunks.append("%s %s\n" % (_ENCODING_HEADER, self.encoding))
        for mergetag in self.mergetag:
            mergetag_chunks = mergetag.as_raw_string().split("\n")

            chunks.append("%s %s\n" % (_MERGETAG_HEADER, mergetag_chunks[0]))
            # Embedded extra header needs leading space
            for chunk in mergetag_chunks[1:]:
                chunks.append(" %s\n" % chunk)

            # No trailing empty line
            chunks[-1] = chunks[-1].rstrip(" \n")
        for k, v in self.extra:
            if "\n" in k or "\n" in v:
                raise AssertionError("newline in extra data: %r -> %r" % (k, v))
            chunks.append("%s %s\n" % (k, v))
        chunks.append("\n") # There must be a new line after the headers
        chunks.append(self._message)
        return chunks

    tree = serializable_property("tree", "Tree that is the state of this commit")

    def _get_parents(self):
        """Return a list of parents of this commit."""
        self._ensure_parsed()
        return self._parents

    def _set_parents(self, value):
        """Set a list of parents of this commit."""
        self._ensure_parsed()
        self._needs_serialization = True
        self._parents = value

    parents = property(_get_parents, _set_parents)

    def _get_extra(self):
        """Return extra settings of this commit."""
        self._ensure_parsed()
        return self._extra

    extra = property(_get_extra)

    author = serializable_property("author",
        "The name of the author of the commit")

    committer = serializable_property("committer",
        "The name of the committer of the commit")

    message = serializable_property("message",
        "The commit message")

    commit_time = serializable_property("commit_time",
        "The timestamp of the commit. As the number of seconds since the epoch.")

    commit_timezone = serializable_property("commit_timezone",
        "The zone the commit time is in")

    author_time = serializable_property("author_time",
        "The timestamp the commit was written. as the number of seconds since the epoch.")

    author_timezone = serializable_property("author_timezone",
        "Returns the zone the author time is in.")

    encoding = serializable_property("encoding",
        "Encoding of the commit message.")

    mergetag = serializable_property("mergetag",
        "Associated signed tag.")


OBJECT_CLASSES = (
    Commit,
    Tree,
    Blob,
    Tag,
    )

_TYPE_MAP = {}

for cls in OBJECT_CLASSES:
    _TYPE_MAP[cls.type_name] = cls
    _TYPE_MAP[cls.type_num] = cls



# Hold on to the pure-python implementations for testing
_parse_tree_py = parse_tree
_sorted_tree_items_py = sorted_tree_items
try:
    # Try to import C versions
    from dulwich._objects import parse_tree, sorted_tree_items
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = object_store
# object_store.py -- Object store for git objects
# Copyright (C) 2008-2012 Jelmer Vernooij <jelmer@samba.org>
#                         and others
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.


"""Git object store interfaces and implementation."""


from cStringIO import StringIO
import errno
import itertools
import os
import stat
import tempfile

from dulwich.diff_tree import (
    tree_changes,
    walk_trees,
    )
from dulwich.errors import (
    NotTreeError,
    )
from dulwich.file import GitFile
from dulwich.objects import (
    Commit,
    ShaFile,
    Tag,
    Tree,
    ZERO_SHA,
    hex_to_sha,
    sha_to_hex,
    hex_to_filename,
    S_ISGITLINK,
    object_class,
    )
from dulwich.pack import (
    Pack,
    PackData,
    PackInflater,
    iter_sha1,
    write_pack_header,
    write_pack_index_v2,
    write_pack_object,
    write_pack_objects,
    compute_file_sha,
    PackIndexer,
    PackStreamCopier,
    )

INFODIR = 'info'
PACKDIR = 'pack'


class BaseObjectStore(object):
    """Object store interface."""

    def determine_wants_all(self, refs):
        return [sha for (ref, sha) in refs.iteritems()
                if not sha in self and not ref.endswith("^{}") and
                   not sha == ZERO_SHA]

    def iter_shas(self, shas):
        """Iterate over the objects for the specified shas.

        :param shas: Iterable object with SHAs
        :return: Object iterator
        """
        return ObjectStoreIterator(self, shas)

    def contains_loose(self, sha):
        """Check if a particular object is present by SHA1 and is loose."""
        raise NotImplementedError(self.contains_loose)

    def contains_packed(self, sha):
        """Check if a particular object is present by SHA1 and is packed."""
        raise NotImplementedError(self.contains_packed)

    def __contains__(self, sha):
        """Check if a particular object is present by SHA1.

        This method makes no distinction between loose and packed objects.
        """
        return self.contains_packed(sha) or self.contains_loose(sha)

    @property
    def packs(self):
        """Iterable of pack objects."""
        raise NotImplementedError

    def get_raw(self, name):
        """Obtain the raw text for an object.

        :param name: sha for the object.
        :return: tuple with numeric type and object contents.
        """
        raise NotImplementedError(self.get_raw)

    def __getitem__(self, sha):
        """Obtain an object by SHA1."""
        type_num, uncomp = self.get_raw(sha)
        return ShaFile.from_raw_string(type_num, uncomp)

    def __iter__(self):
        """Iterate over the SHAs that are present in this store."""
        raise NotImplementedError(self.__iter__)

    def add_object(self, obj):
        """Add a single object to this object store.

        """
        raise NotImplementedError(self.add_object)

    def add_objects(self, objects):
        """Add a set of objects to this object store.

        :param objects: Iterable over a list of objects.
        """
        raise NotImplementedError(self.add_objects)

    def tree_changes(self, source, target, want_unchanged=False):
        """Find the differences between the contents of two trees

        :param source: SHA1 of the source tree
        :param target: SHA1 of the target tree
        :param want_unchanged: Whether unchanged files should be reported
        :return: Iterator over tuples with
            (oldpath, newpath), (oldmode, newmode), (oldsha, newsha)
        """
        for change in tree_changes(self, source, target,
                                   want_unchanged=want_unchanged):
            yield ((change.old.path, change.new.path),
                   (change.old.mode, change.new.mode),
                   (change.old.sha, change.new.sha))

    def iter_tree_contents(self, tree_id, include_trees=False):
        """Iterate the contents of a tree and all subtrees.

        Iteration is depth-first pre-order, as in e.g. os.walk.

        :param tree_id: SHA1 of the tree.
        :param include_trees: If True, include tree objects in the iteration.
        :return: Iterator over TreeEntry namedtuples for all the objects in a
            tree.
        """
        for entry, _ in walk_trees(self, tree_id, None):
            if not stat.S_ISDIR(entry.mode) or include_trees:
                yield entry

    def find_missing_objects(self, haves, wants, progress=None,
                             get_tagged=None):
        """Find the missing objects required for a set of revisions.

        :param haves: Iterable over SHAs already in common.
        :param wants: Iterable over SHAs of objects to fetch.
        :param progress: Simple progress function that will be called with
            updated progress strings.
        :param get_tagged: Function that returns a dict of pointed-to sha -> tag
            sha for including tags.
        :return: Iterator over (sha, path) pairs.
        """
        finder = MissingObjectFinder(self, haves, wants, progress, get_tagged)
        return iter(finder.next, None)

    def find_common_revisions(self, graphwalker):
        """Find which revisions this store has in common using graphwalker.

        :param graphwalker: A graphwalker object.
        :return: List of SHAs that are in common
        """
        haves = []
        sha = graphwalker.next()
        while sha:
            if sha in self:
                haves.append(sha)
                graphwalker.ack(sha)
            sha = graphwalker.next()
        return haves

    def get_graph_walker(self, heads):
        """Obtain a graph walker for this object store.

        :param heads: Local heads to start search with
        :return: GraphWalker object
        """
        return ObjectStoreGraphWalker(heads, lambda sha: self[sha].parents)

    def generate_pack_contents(self, have, want, progress=None):
        """Iterate over the contents of a pack file.

        :param have: List of SHA1s of objects that should not be sent
        :param want: List of SHA1s of objects that should be sent
        :param progress: Optional progress reporting method
        """
        return self.iter_shas(self.find_missing_objects(have, want, progress))

    def peel_sha(self, sha):
        """Peel all tags from a SHA.

        :param sha: The object SHA to peel.
        :return: The fully-peeled SHA1 of a tag object, after peeling all
            intermediate tags; if the original ref does not point to a tag, this
            will equal the original SHA1.
        """
        obj = self[sha]
        obj_class = object_class(obj.type_name)
        while obj_class is Tag:
            obj_class, sha = obj.object
            obj = self[sha]
        return obj

    def _collect_ancestors(self, heads, common=set()):
        """Collect all ancestors of heads up to (excluding) those in common.

        :param heads: commits to start from
        :param common: commits to end at, or empty set to walk repository
            completely
        :return: a tuple (A, B) where A - all commits reachable
            from heads but not present in common, B - common (shared) elements
            that are directly reachable from heads
        """
        bases = set()
        commits = set()
        queue = []
        queue.extend(heads)
        while queue:
            e = queue.pop(0)
            if e in common:
                bases.add(e)
            elif e not in commits:
                commits.add(e)
                cmt = self[e]
                queue.extend(cmt.parents)
        return (commits, bases)

    def close(self):
        """Close any files opened by this object store."""
        # Default implementation is a NO-OP


class PackBasedObjectStore(BaseObjectStore):

    def __init__(self):
        self._pack_cache = None

    @property
    def alternates(self):
        return []

    def contains_packed(self, sha):
        """Check if a particular object is present by SHA1 and is packed.

        This does not check alternates.
        """
        for pack in self.packs:
            if sha in pack:
                return True
        return False

    def __contains__(self, sha):
        """Check if a particular object is present by SHA1.

        This method makes no distinction between loose and packed objects.
        """
        if self.contains_packed(sha) or self.contains_loose(sha):
            return True
        for alternate in self.alternates:
            if sha in alternate:
                return True
        return False

    def _load_packs(self):
        raise NotImplementedError(self._load_packs)

    def _pack_cache_stale(self):
        """Check whether the pack cache is stale."""
        raise NotImplementedError(self._pack_cache_stale)

    def _add_known_pack(self, pack):
        """Add a newly appeared pack to the cache by path.

        """
        if self._pack_cache is not None:
            self._pack_cache.append(pack)

    def close(self):
        pack_cache = self._pack_cache
        self._pack_cache = None
        while pack_cache:
            pack = pack_cache.pop()
            pack.close()

    @property
    def packs(self):
        """List with pack objects."""
        if self._pack_cache is None or self._pack_cache_stale():
            self._pack_cache = self._load_packs()
        return self._pack_cache

    def _iter_alternate_objects(self):
        """Iterate over the SHAs of all the objects in alternate stores."""
        for alternate in self.alternates:
            for alternate_object in alternate:
                yield alternate_object

    def _iter_loose_objects(self):
        """Iterate over the SHAs of all loose objects."""
        raise NotImplementedError(self._iter_loose_objects)

    def _get_loose_object(self, sha):
        raise NotImplementedError(self._get_loose_object)

    def _remove_loose_object(self, sha):
        raise NotImplementedError(self._remove_loose_object)

    def pack_loose_objects(self):
        """Pack loose objects.

        :return: Number of objects packed
        """
        objects = set()
        for sha in self._iter_loose_objects():
            objects.add((self._get_loose_object(sha), None))
        self.add_objects(list(objects))
        for obj, path in objects:
            self._remove_loose_object(obj.id)
        return len(objects)

    def __iter__(self):
        """Iterate over the SHAs that are present in this store."""
        iterables = self.packs + [self._iter_loose_objects()] + [self._iter_alternate_objects()]
        return itertools.chain(*iterables)

    def contains_loose(self, sha):
        """Check if a particular object is present by SHA1 and is loose.

        This does not check alternates.
        """
        return self._get_loose_object(sha) is not None

    def get_raw(self, name):
        """Obtain the raw text for an object.

        :param name: sha for the object.
        :return: tuple with numeric type and object contents.
        """
        if len(name) == 40:
            sha = hex_to_sha(name)
            hexsha = name
        elif len(name) == 20:
            sha = name
            hexsha = None
        else:
            raise AssertionError("Invalid object name %r" % name)
        for pack in self.packs:
            try:
                return pack.get_raw(sha)
            except KeyError:
                pass
        if hexsha is None:
            hexsha = sha_to_hex(name)
        ret = self._get_loose_object(hexsha)
        if ret is not None:
            return ret.type_num, ret.as_raw_string()
        for alternate in self.alternates:
            try:
                return alternate.get_raw(hexsha)
            except KeyError:
                pass
        raise KeyError(hexsha)

    def add_objects(self, objects):
        """Add a set of objects to this object store.

        :param objects: Iterable over objects, should support __len__.
        :return: Pack object of the objects written.
        """
        if len(objects) == 0:
            # Don't bother writing an empty pack file
            return
        f, commit, abort = self.add_pack()
        try:
            write_pack_objects(f, objects)
        except:
            abort()
            raise
        else:
            return commit()


class DiskObjectStore(PackBasedObjectStore):
    """Git-style object store that exists on disk."""

    def __init__(self, path):
        """Open an object store.

        :param path: Path of the object store.
        """
        super(DiskObjectStore, self).__init__()
        self.path = path
        self.pack_dir = os.path.join(self.path, PACKDIR)
        self._pack_cache_time = 0
        self._alternates = None

    @property
    def alternates(self):
        if self._alternates is not None:
            return self._alternates
        self._alternates = []
        for path in self._read_alternate_paths():
            self._alternates.append(DiskObjectStore(path))
        return self._alternates

    def _read_alternate_paths(self):
        try:
            f = GitFile(os.path.join(self.path, "info", "alternates"),
                    'rb')
        except (OSError, IOError), e:
            if e.errno == errno.ENOENT:
                return []
            raise
        ret = []
        try:
            for l in f.readlines():
                l = l.rstrip("\n")
                if l[0] == "#":
                    continue
                if os.path.isabs(l):
                    ret.append(l)
                else:
                    ret.append(os.path.join(self.path, l))
            return ret
        finally:
            f.close()

    def add_alternate_path(self, path):
        """Add an alternate path to this object store.
        """
        try:
            os.mkdir(os.path.join(self.path, "info"))
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        alternates_path = os.path.join(self.path, "info/alternates")
        f = GitFile(alternates_path, 'wb')
        try:
            try:
                orig_f = open(alternates_path, 'rb')
            except (OSError, IOError), e:
                if e.errno != errno.ENOENT:
                    raise
            else:
                try:
                    f.write(orig_f.read())
                finally:
                    orig_f.close()
            f.write("%s\n" % path)
        finally:
            f.close()

        if not os.path.isabs(path):
            path = os.path.join(self.path, path)
        self.alternates.append(DiskObjectStore(path))

    def _load_packs(self):
        pack_files = []
        try:
            self._pack_cache_time = os.stat(self.pack_dir).st_mtime
            pack_dir_contents = os.listdir(self.pack_dir)
            for name in pack_dir_contents:
                # TODO: verify that idx exists first
                if name.startswith("pack-") and name.endswith(".pack"):
                    filename = os.path.join(self.pack_dir, name)
                    pack_files.append((os.stat(filename).st_mtime, filename))
        except OSError, e:
            if e.errno == errno.ENOENT:
                return []
            raise
        pack_files.sort(reverse=True)
        suffix_len = len(".pack")
        return [Pack(f[:-suffix_len]) for _, f in pack_files]

    def _pack_cache_stale(self):
        try:
            return os.stat(self.pack_dir).st_mtime > self._pack_cache_time
        except OSError, e:
            if e.errno == errno.ENOENT:
                return True
            raise

    def _get_shafile_path(self, sha):
        # Check from object dir
        return hex_to_filename(self.path, sha)

    def _iter_loose_objects(self):
        for base in os.listdir(self.path):
            if len(base) != 2:
                continue
            for rest in os.listdir(os.path.join(self.path, base)):
                yield base+rest

    def _get_loose_object(self, sha):
        path = self._get_shafile_path(sha)
        try:
            return ShaFile.from_path(path)
        except (OSError, IOError), e:
            if e.errno == errno.ENOENT:
                return None
            raise

    def _remove_loose_object(self, sha):
        os.remove(self._get_shafile_path(sha))

    def _complete_thin_pack(self, f, path, copier, indexer):
        """Move a specific file containing a pack into the pack directory.

        :note: The file should be on the same file system as the
            packs directory.

        :param f: Open file object for the pack.
        :param path: Path to the pack file.
        :param copier: A PackStreamCopier to use for writing pack data.
        :param indexer: A PackIndexer for indexing the pack.
        """
        entries = list(indexer)

        # Update the header with the new number of objects.
        f.seek(0)
        write_pack_header(f, len(entries) + len(indexer.ext_refs()))

        # Must flush before reading (http://bugs.python.org/issue3207)
        f.flush()

        # Rescan the rest of the pack, computing the SHA with the new header.
        new_sha = compute_file_sha(f, end_ofs=-20)

        # Must reposition before writing (http://bugs.python.org/issue3207)
        f.seek(0, os.SEEK_CUR)

        # Complete the pack.
        for ext_sha in indexer.ext_refs():
            assert len(ext_sha) == 20
            type_num, data = self.get_raw(ext_sha)
            offset = f.tell()
            crc32 = write_pack_object(f, type_num, data, sha=new_sha)
            entries.append((ext_sha, offset, crc32))
        pack_sha = new_sha.digest()
        f.write(pack_sha)
        f.close()

        # Move the pack in.
        entries.sort()
        pack_base_name = os.path.join(
          self.pack_dir, 'pack-' + iter_sha1(e[0] for e in entries))
        os.rename(path, pack_base_name + '.pack')

        # Write the index.
        index_file = GitFile(pack_base_name + '.idx', 'wb')
        try:
            write_pack_index_v2(index_file, entries, pack_sha)
            index_file.close()
        finally:
            index_file.abort()

        # Add the pack to the store and return it.
        final_pack = Pack(pack_base_name)
        final_pack.check_length_and_checksum()
        self._add_known_pack(final_pack)
        return final_pack

    def add_thin_pack(self, read_all, read_some):
        """Add a new thin pack to this object store.

        Thin packs are packs that contain deltas with parents that exist outside
        the pack. They should never be placed in the object store directly, and
        always indexed and completed as they are copied.

        :param read_all: Read function that blocks until the number of requested
            bytes are read.
        :param read_some: Read function that returns at least one byte, but may
            not return the number of bytes requested.
        :return: A Pack object pointing at the now-completed thin pack in the
            objects/pack directory.
        """
        fd, path = tempfile.mkstemp(dir=self.path, prefix='tmp_pack_')
        f = os.fdopen(fd, 'w+b')

        try:
            indexer = PackIndexer(f, resolve_ext_ref=self.get_raw)
            copier = PackStreamCopier(read_all, read_some, f,
                                      delta_iter=indexer)
            copier.verify()
            return self._complete_thin_pack(f, path, copier, indexer)
        finally:
            f.close()

    def move_in_pack(self, path):
        """Move a specific file containing a pack into the pack directory.

        :note: The file should be on the same file system as the
            packs directory.

        :param path: Path to the pack file.
        """
        p = PackData(path)
        entries = p.sorted_entries()
        basename = os.path.join(self.pack_dir,
            "pack-%s" % iter_sha1(entry[0] for entry in entries))
        f = GitFile(basename+".idx", "wb")
        try:
            write_pack_index_v2(f, entries, p.get_stored_checksum())
        finally:
            f.close()
        p.close()
        os.rename(path, basename + ".pack")
        final_pack = Pack(basename)
        self._add_known_pack(final_pack)
        return final_pack

    def add_pack(self):
        """Add a new pack to this object store.

        :return: Fileobject to write to, a commit function to
            call when the pack is finished and an abort
            function.
        """
        fd, path = tempfile.mkstemp(dir=self.pack_dir, suffix=".pack")
        f = os.fdopen(fd, 'wb')
        def commit():
            os.fsync(fd)
            f.close()
            if os.path.getsize(path) > 0:
                return self.move_in_pack(path)
            else:
                os.remove(path)
                return None
        def abort():
            f.close()
            os.remove(path)
        return f, commit, abort

    def add_object(self, obj):
        """Add a single object to this object store.

        :param obj: Object to add
        """
        dir = os.path.join(self.path, obj.id[:2])
        try:
            os.mkdir(dir)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        path = os.path.join(dir, obj.id[2:])
        if os.path.exists(path):
            return # Already there, no need to write again
        f = GitFile(path, 'wb')
        try:
            f.write(obj.as_legacy_object())
        finally:
            f.close()

    @classmethod
    def init(cls, path):
        try:
            os.mkdir(path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        os.mkdir(os.path.join(path, "info"))
        os.mkdir(os.path.join(path, PACKDIR))
        return cls(path)


class MemoryObjectStore(BaseObjectStore):
    """Object store that keeps all objects in memory."""

    def __init__(self):
        super(MemoryObjectStore, self).__init__()
        self._data = {}

    def _to_hexsha(self, sha):
        if len(sha) == 40:
            return sha
        elif len(sha) == 20:
            return sha_to_hex(sha)
        else:
            raise ValueError("Invalid sha %r" % (sha,))

    def contains_loose(self, sha):
        """Check if a particular object is present by SHA1 and is loose."""
        return self._to_hexsha(sha) in self._data

    def contains_packed(self, sha):
        """Check if a particular object is present by SHA1 and is packed."""
        return False

    def __iter__(self):
        """Iterate over the SHAs that are present in this store."""
        return self._data.iterkeys()

    @property
    def packs(self):
        """List with pack objects."""
        return []

    def get_raw(self, name):
        """Obtain the raw text for an object.

        :param name: sha for the object.
        :return: tuple with numeric type and object contents.
        """
        obj = self[self._to_hexsha(name)]
        return obj.type_num, obj.as_raw_string()

    def __getitem__(self, name):
        return self._data[self._to_hexsha(name)]

    def __delitem__(self, name):
        """Delete an object from this store, for testing only."""
        del self._data[self._to_hexsha(name)]

    def add_object(self, obj):
        """Add a single object to this object store.

        """
        self._data[obj.id] = obj

    def add_objects(self, objects):
        """Add a set of objects to this object store.

        :param objects: Iterable over a list of objects.
        """
        for obj, path in objects:
            self._data[obj.id] = obj

    def add_pack(self):
        """Add a new pack to this object store.

        Because this object store doesn't support packs, we extract and add the
        individual objects.

        :return: Fileobject to write to and a commit function to
            call when the pack is finished.
        """
        f = StringIO()
        def commit():
            p = PackData.from_file(StringIO(f.getvalue()), f.tell())
            f.close()
            for obj in PackInflater.for_pack_data(p):
                self._data[obj.id] = obj
        def abort():
            pass
        return f, commit, abort

    def _complete_thin_pack(self, f, indexer):
        """Complete a thin pack by adding external references.

        :param f: Open file object for the pack.
        :param indexer: A PackIndexer for indexing the pack.
        """
        entries = list(indexer)

        # Update the header with the new number of objects.
        f.seek(0)
        write_pack_header(f, len(entries) + len(indexer.ext_refs()))

        # Rescan the rest of the pack, computing the SHA with the new header.
        new_sha = compute_file_sha(f, end_ofs=-20)

        # Complete the pack.
        for ext_sha in indexer.ext_refs():
            assert len(ext_sha) == 20
            type_num, data = self.get_raw(ext_sha)
            write_pack_object(f, type_num, data, sha=new_sha)
        pack_sha = new_sha.digest()
        f.write(pack_sha)

    def add_thin_pack(self, read_all, read_some):
        """Add a new thin pack to this object store.

        Thin packs are packs that contain deltas with parents that exist outside
        the pack. Because this object store doesn't support packs, we extract
        and add the individual objects.

        :param read_all: Read function that blocks until the number of requested
            bytes are read.
        :param read_some: Read function that returns at least one byte, but may
            not return the number of bytes requested.
        """
        f, commit, abort = self.add_pack()
        try:
            indexer = PackIndexer(f, resolve_ext_ref=self.get_raw)
            copier = PackStreamCopier(read_all, read_some, f, delta_iter=indexer)
            copier.verify()
            self._complete_thin_pack(f, indexer)
        except:
            abort()
            raise
        else:
            commit()


class ObjectImporter(object):
    """Interface for importing objects."""

    def __init__(self, count):
        """Create a new ObjectImporter.

        :param count: Number of objects that's going to be imported.
        """
        self.count = count

    def add_object(self, object):
        """Add an object."""
        raise NotImplementedError(self.add_object)

    def finish(self, object):
        """Finish the import and write objects to disk."""
        raise NotImplementedError(self.finish)


class ObjectIterator(object):
    """Interface for iterating over objects."""

    def iterobjects(self):
        raise NotImplementedError(self.iterobjects)


class ObjectStoreIterator(ObjectIterator):
    """ObjectIterator that works on top of an ObjectStore."""

    def __init__(self, store, sha_iter):
        """Create a new ObjectIterator.

        :param store: Object store to retrieve from
        :param sha_iter: Iterator over (sha, path) tuples
        """
        self.store = store
        self.sha_iter = sha_iter
        self._shas = []

    def __iter__(self):
        """Yield tuple with next object and path."""
        for sha, path in self.itershas():
            yield self.store[sha], path

    def iterobjects(self):
        """Iterate over just the objects."""
        for o, path in self:
            yield o

    def itershas(self):
        """Iterate over the SHAs."""
        for sha in self._shas:
            yield sha
        for sha in self.sha_iter:
            self._shas.append(sha)
            yield sha

    def __contains__(self, needle):
        """Check if an object is present.

        :note: This checks if the object is present in
            the underlying object store, not if it would
            be yielded by the iterator.

        :param needle: SHA1 of the object to check for
        """
        return needle in self.store

    def __getitem__(self, key):
        """Find an object by SHA1.

        :note: This retrieves the object from the underlying
            object store. It will also succeed if the object would
            not be returned by the iterator.
        """
        return self.store[key]

    def __len__(self):
        """Return the number of objects."""
        return len(list(self.itershas()))


def tree_lookup_path(lookup_obj, root_sha, path):
    """Look up an object in a Git tree.

    :param lookup_obj: Callback for retrieving object by SHA1
    :param root_sha: SHA1 of the root tree
    :param path: Path to lookup
    :return: A tuple of (mode, SHA) of the resulting path.
    """
    tree = lookup_obj(root_sha)
    if not isinstance(tree, Tree):
        raise NotTreeError(root_sha)
    return tree.lookup_path(lookup_obj, path)


def _collect_filetree_revs(obj_store, tree_sha, kset):
    """Collect SHA1s of files and directories for specified tree.

    :param obj_store: Object store to get objects by SHA from
    :param tree_sha: tree reference to walk
    :param kset: set to fill with references to files and directories
    """
    filetree = obj_store[tree_sha]
    for name, mode, sha in filetree.iteritems():
       if not S_ISGITLINK(mode) and sha not in kset:
           kset.add(sha)
           if stat.S_ISDIR(mode):
               _collect_filetree_revs(obj_store, sha, kset)


def _split_commits_and_tags(obj_store, lst, ignore_unknown=False):
    """Split object id list into two list with commit SHA1s and tag SHA1s.

    Commits referenced by tags are included into commits
    list as well. Only SHA1s known in this repository will get
    through, and unless ignore_unknown argument is True, KeyError
    is thrown for SHA1 missing in the repository

    :param obj_store: Object store to get objects by SHA1 from
    :param lst: Collection of commit and tag SHAs
    :param ignore_unknown: True to skip SHA1 missing in the repository
        silently.
    :return: A tuple of (commits, tags) SHA1s
    """
    commits = set()
    tags = set()
    for e in lst:
        try:
            o = obj_store[e]
        except KeyError:
            if not ignore_unknown:
                raise
        else:
            if isinstance(o, Commit):
                commits.add(e)
            elif isinstance(o, Tag):
                tags.add(e)
                commits.add(o.object[1])
            else:
                raise KeyError('Not a commit or a tag: %s' % e)
    return (commits, tags)


class MissingObjectFinder(object):
    """Find the objects missing from another object store.

    :param object_store: Object store containing at least all objects to be
        sent
    :param haves: SHA1s of commits not to send (already present in target)
    :param wants: SHA1s of commits to send
    :param progress: Optional function to report progress to.
    :param get_tagged: Function that returns a dict of pointed-to sha -> tag
        sha for including tags.
    :param tagged: dict of pointed-to sha -> tag sha for including tags
    """

    def __init__(self, object_store, haves, wants, progress=None,
                 get_tagged=None):
        self.object_store = object_store
        # process Commits and Tags differently
        # Note, while haves may list commits/tags not available locally,
        # and such SHAs would get filtered out by _split_commits_and_tags,
        # wants shall list only known SHAs, and otherwise
        # _split_commits_and_tags fails with KeyError
        have_commits, have_tags = \
                _split_commits_and_tags(object_store, haves, True)
        want_commits, want_tags = \
                _split_commits_and_tags(object_store, wants, False)
        # all_ancestors is a set of commits that shall not be sent
        # (complete repository up to 'haves')
        all_ancestors = object_store._collect_ancestors(have_commits)[0]
        # all_missing - complete set of commits between haves and wants
        # common - commits from all_ancestors we hit into while
        # traversing parent hierarchy of wants
        missing_commits, common_commits = \
            object_store._collect_ancestors(want_commits, all_ancestors)
        self.sha_done = set()
        # Now, fill sha_done with commits and revisions of
        # files and directories known to be both locally
        # and on target. Thus these commits and files
        # won't get selected for fetch
        for h in common_commits:
            self.sha_done.add(h)
            cmt = object_store[h]
            _collect_filetree_revs(object_store, cmt.tree, self.sha_done)
        # record tags we have as visited, too
        for t in have_tags:
            self.sha_done.add(t)

        missing_tags = want_tags.difference(have_tags)
        # in fact, what we 'want' is commits and tags
        # we've found missing
        wants = missing_commits.union(missing_tags)

        self.objects_to_send = set([(w, None, False) for w in wants])

        if progress is None:
            self.progress = lambda x: None
        else:
            self.progress = progress
        self._tagged = get_tagged and get_tagged() or {}

    def add_todo(self, entries):
        self.objects_to_send.update([e for e in entries
                                     if not e[0] in self.sha_done])

    def next(self):
        while True:
            if not self.objects_to_send:
                return None
            (sha, name, leaf) = self.objects_to_send.pop()
            if sha not in self.sha_done:
                break
        if not leaf:
            o = self.object_store[sha]
            if isinstance(o, Commit):
                self.add_todo([(o.tree, "", False)])
            elif isinstance(o, Tree):
                self.add_todo([(s, n, not stat.S_ISDIR(m))
                               for n, m, s in o.iteritems()
                               if not S_ISGITLINK(m)])
            elif isinstance(o, Tag):
                self.add_todo([(o.object[1], None, False)])
        if sha in self._tagged:
            self.add_todo([(self._tagged[sha], None, True)])
        self.sha_done.add(sha)
        self.progress("counting objects: %d\r" % len(self.sha_done))
        return (sha, name)


class ObjectStoreGraphWalker(object):
    """Graph walker that finds what commits are missing from an object store.

    :ivar heads: Revisions without descendants in the local repo
    :ivar get_parents: Function to retrieve parents in the local repo
    """

    def __init__(self, local_heads, get_parents):
        """Create a new instance.

        :param local_heads: Heads to start search with
        :param get_parents: Function for finding the parents of a SHA1.
        """
        self.heads = set(local_heads)
        self.get_parents = get_parents
        self.parents = {}

    def ack(self, sha):
        """Ack that a revision and its ancestors are present in the source."""
        ancestors = set([sha])

        # stop if we run out of heads to remove
        while self.heads:
            for a in ancestors:
                if a in self.heads:
                    self.heads.remove(a)

            # collect all ancestors
            new_ancestors = set()
            for a in ancestors:
                ps = self.parents.get(a)
                if ps is not None:
                    new_ancestors.update(ps)
                self.parents[a] = None

            # no more ancestors; stop
            if not new_ancestors:
                break

            ancestors = new_ancestors

    def next(self):
        """Iterate over ancestors of heads in the target."""
        if self.heads:
            ret = self.heads.pop()
            ps = self.get_parents(ret)
            self.parents[ret] = ps
            self.heads.update([p for p in ps if not p in self.parents])
            return ret
        return None

########NEW FILE########
__FILENAME__ = pack
# pack.py -- For dealing with packed git objects.
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Classes for dealing with packed git objects.

A pack is a compact representation of a bunch of objects, stored
using deltas where possible.

They have two parts, the pack file, which stores the data, and an index
that tells you where the data is.

To find an object you look in all of the index files 'til you find a
match for the object name. You then use the pointer got from this as
a pointer in to the corresponding packfile.
"""

try:
    from collections import defaultdict
except ImportError:
    from dulwich._compat import defaultdict

import binascii
from cStringIO import (
    StringIO,
    )
from collections import (
    deque,
    )
import difflib
from itertools import (
    chain,
    imap,
    izip,
    )
try:
    import mmap
except ImportError:
    has_mmap = False
else:
    has_mmap = True
import os
import struct
try:
    from struct import unpack_from
except ImportError:
    from dulwich._compat import unpack_from
import sys
import warnings
import zlib

from dulwich.errors import (
    ApplyDeltaError,
    ChecksumMismatch,
    )
from dulwich.file import GitFile
from dulwich.lru_cache import (
    LRUSizeCache,
    )
from dulwich._compat import (
    make_sha,
    SEEK_CUR,
    SEEK_END,
    )
from dulwich.objects import (
    ShaFile,
    hex_to_sha,
    sha_to_hex,
    object_header,
    )

supports_mmap_offset = (sys.version_info[0] >= 3 or
        (sys.version_info[0] == 2 and sys.version_info[1] >= 6))


OFS_DELTA = 6
REF_DELTA = 7

DELTA_TYPES = (OFS_DELTA, REF_DELTA)


def take_msb_bytes(read, crc32=None):
    """Read bytes marked with most significant bit.

    :param read: Read function
    """
    ret = []
    while len(ret) == 0 or ret[-1] & 0x80:
        b = read(1)
        if crc32 is not None:
            crc32 = binascii.crc32(b, crc32)
        ret.append(ord(b))
    return ret, crc32


class UnpackedObject(object):
    """Class encapsulating an object unpacked from a pack file.

    These objects should only be created from within unpack_object. Most
    members start out as empty and are filled in at various points by
    read_zlib_chunks, unpack_object, DeltaChainIterator, etc.

    End users of this object should take care that the function they're getting
    this object from is guaranteed to set the members they need.
    """

    __slots__ = [
      'offset',         # Offset in its pack.
      '_sha',           # Cached binary SHA.
      'obj_type_num',   # Type of this object.
      'obj_chunks',     # Decompressed and delta-resolved chunks.
      'pack_type_num',  # Type of this object in the pack (may be a delta).
      'delta_base',     # Delta base offset or SHA.
      'comp_chunks',    # Compressed object chunks.
      'decomp_chunks',  # Decompressed object chunks.
      'decomp_len',     # Decompressed length of this object.
      'crc32',          # CRC32.
      ]

    # TODO(dborowitz): read_zlib_chunks and unpack_object could very well be
    # methods of this object.
    def __init__(self, pack_type_num, delta_base, decomp_len, crc32):
        self.offset = None
        self._sha = None
        self.pack_type_num = pack_type_num
        self.delta_base = delta_base
        self.comp_chunks = None
        self.decomp_chunks = []
        self.decomp_len = decomp_len
        self.crc32 = crc32

        if pack_type_num in DELTA_TYPES:
            self.obj_type_num = None
            self.obj_chunks = None
        else:
            self.obj_type_num = pack_type_num
            self.obj_chunks = self.decomp_chunks
            self.delta_base = delta_base

    def sha(self):
        """Return the binary SHA of this object."""
        if self._sha is None:
            self._sha = obj_sha(self.obj_type_num, self.obj_chunks)
        return self._sha

    def sha_file(self):
        """Return a ShaFile from this object."""
        return ShaFile.from_raw_chunks(self.obj_type_num, self.obj_chunks)

    # Only provided for backwards compatibility with code that expects either
    # chunks or a delta tuple.
    def _obj(self):
        """Return the decompressed chunks, or (delta base, delta chunks)."""
        if self.pack_type_num in DELTA_TYPES:
            return (self.delta_base, self.decomp_chunks)
        else:
            return self.decomp_chunks

    def __eq__(self, other):
        if not isinstance(other, UnpackedObject):
            return False
        for slot in self.__slots__:
            if getattr(self, slot) != getattr(other, slot):
                return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        data = ['%s=%r' % (s, getattr(self, s)) for s in self.__slots__]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(data))


_ZLIB_BUFSIZE = 4096


def read_zlib_chunks(read_some, unpacked, include_comp=False,
                     buffer_size=_ZLIB_BUFSIZE):
    """Read zlib data from a buffer.

    This function requires that the buffer have additional data following the
    compressed data, which is guaranteed to be the case for git pack files.

    :param read_some: Read function that returns at least one byte, but may
        return less than the requested size.
    :param unpacked: An UnpackedObject to write result data to. If its crc32
        attr is not None, the CRC32 of the compressed bytes will be computed
        using this starting CRC32.
        After this function, will have the following attrs set:
        * comp_chunks    (if include_comp is True)
        * decomp_chunks
        * decomp_len
        * crc32
    :param include_comp: If True, include compressed data in the result.
    :param buffer_size: Size of the read buffer.
    :return: Leftover unused data from the decompression.
    :raise zlib.error: if a decompression error occurred.
    """
    if unpacked.decomp_len <= -1:
        raise ValueError('non-negative zlib data stream size expected')
    decomp_obj = zlib.decompressobj()

    comp_chunks = []
    decomp_chunks = unpacked.decomp_chunks
    decomp_len = 0
    crc32 = unpacked.crc32

    while True:
        add = read_some(buffer_size)
        if not add:
            raise zlib.error('EOF before end of zlib stream')
        comp_chunks.append(add)
        decomp = decomp_obj.decompress(add)
        decomp_len += len(decomp)
        decomp_chunks.append(decomp)
        unused = decomp_obj.unused_data
        if unused:
            left = len(unused)
            if crc32 is not None:
                crc32 = binascii.crc32(add[:-left], crc32)
            if include_comp:
                comp_chunks[-1] = add[:-left]
            break
        elif crc32 is not None:
            crc32 = binascii.crc32(add, crc32)
    if crc32 is not None:
        crc32 &= 0xffffffff

    if decomp_len != unpacked.decomp_len:
        raise zlib.error('decompressed data does not match expected size')

    unpacked.crc32 = crc32
    if include_comp:
        unpacked.comp_chunks = comp_chunks
    return unused


def iter_sha1(iter):
    """Return the hexdigest of the SHA1 over a set of names.

    :param iter: Iterator over string objects
    :return: 40-byte hex sha1 digest
    """
    sha1 = make_sha()
    for name in iter:
        sha1.update(name)
    return sha1.hexdigest()


def load_pack_index(path):
    """Load an index file by path.

    :param filename: Path to the index file
    :return: A PackIndex loaded from the given path
    """
    f = GitFile(path, 'rb')
    try:
        return load_pack_index_file(path, f)
    finally:
        f.close()


def _load_file_contents(f, size=None):
    fileno = getattr(f, 'fileno', None)
    # Attempt to use mmap if possible
    if fileno is not None:
        fd = f.fileno()
        if size is None:
            size = os.fstat(fd).st_size
        if has_mmap:
            try:
                contents = mmap.mmap(fd, size, access=mmap.ACCESS_READ)
            except mmap.error:
                # Perhaps a socket?
                pass
            else:
                return contents, size
    contents = f.read()
    size = len(contents)
    return contents, size


def load_pack_index_file(path, f):
    """Load an index file from a file-like object.

    :param path: Path for the index file
    :param f: File-like object
    :return: A PackIndex loaded from the given file
    """
    contents, size = _load_file_contents(f)
    if contents[:4] == '\377tOc':
        version = struct.unpack('>L', contents[4:8])[0]
        if version == 2:
            return PackIndex2(path, file=f, contents=contents,
                size=size)
        else:
            raise KeyError('Unknown pack index format %d' % version)
    else:
        return PackIndex1(path, file=f, contents=contents, size=size)


def bisect_find_sha(start, end, sha, unpack_name):
    """Find a SHA in a data blob with sorted SHAs.

    :param start: Start index of range to search
    :param end: End index of range to search
    :param sha: Sha to find
    :param unpack_name: Callback to retrieve SHA by index
    :return: Index of the SHA, or None if it wasn't found
    """
    assert start <= end
    while start <= end:
        i = (start + end)/2
        file_sha = unpack_name(i)
        x = cmp(file_sha, sha)
        if x < 0:
            start = i + 1
        elif x > 0:
            end = i - 1
        else:
            return i
    return None


class PackIndex(object):
    """An index in to a packfile.

    Given a sha id of an object a pack index can tell you the location in the
    packfile of that object if it has it.
    """

    def __eq__(self, other):
        if not isinstance(other, PackIndex):
            return False

        for (name1, _, _), (name2, _, _) in izip(self.iterentries(),
                                                 other.iterentries()):
            if name1 != name2:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        """Return the number of entries in this pack index."""
        raise NotImplementedError(self.__len__)

    def __iter__(self):
        """Iterate over the SHAs in this pack."""
        return imap(sha_to_hex, self._itersha())

    def iterentries(self):
        """Iterate over the entries in this pack index.

        :return: iterator over tuples with object name, offset in packfile and
            crc32 checksum.
        """
        raise NotImplementedError(self.iterentries)

    def get_pack_checksum(self):
        """Return the SHA1 checksum stored for the corresponding packfile.

        :return: 20-byte binary digest
        """
        raise NotImplementedError(self.get_pack_checksum)

    def object_index(self, sha):
        """Return the index in to the corresponding packfile for the object.

        Given the name of an object it will return the offset that object
        lives at within the corresponding pack file. If the pack file doesn't
        have the object then None will be returned.
        """
        if len(sha) == 40:
            sha = hex_to_sha(sha)
        return self._object_index(sha)

    def _object_index(self, sha):
        """See object_index.

        :param sha: A *binary* SHA string. (20 characters long)_
        """
        raise NotImplementedError(self._object_index)

    def objects_sha1(self):
        """Return the hex SHA1 over all the shas of all objects in this pack.

        :note: This is used for the filename of the pack.
        """
        return iter_sha1(self._itersha())

    def _itersha(self):
        """Yield all the SHA1's of the objects in the index, sorted."""
        raise NotImplementedError(self._itersha)


class MemoryPackIndex(PackIndex):
    """Pack index that is stored entirely in memory."""

    def __init__(self, entries, pack_checksum=None):
        """Create a new MemoryPackIndex.

        :param entries: Sequence of name, idx, crc32 (sorted)
        :param pack_checksum: Optional pack checksum
        """
        self._by_sha = {}
        for name, idx, crc32 in entries:
            self._by_sha[name] = idx
        self._entries = entries
        self._pack_checksum = pack_checksum

    def get_pack_checksum(self):
        return self._pack_checksum

    def __len__(self):
        return len(self._entries)

    def _object_index(self, sha):
        return self._by_sha[sha][0]

    def _itersha(self):
        return iter(self._by_sha)

    def iterentries(self):
        return iter(self._entries)


class FilePackIndex(PackIndex):
    """Pack index that is based on a file.

    To do the loop it opens the file, and indexes first 256 4 byte groups
    with the first byte of the sha id. The value in the four byte group indexed
    is the end of the group that shares the same starting byte. Subtract one
    from the starting byte and index again to find the start of the group.
    The values are sorted by sha id within the group, so do the math to find
    the start and end offset and then bisect in to find if the value is present.
    """

    def __init__(self, filename, file=None, contents=None, size=None):
        """Create a pack index object.

        Provide it with the name of the index file to consider, and it will map
        it whenever required.
        """
        self._filename = filename
        # Take the size now, so it can be checked each time we map the file to
        # ensure that it hasn't changed.
        if file is None:
            self._file = GitFile(filename, 'rb')
        else:
            self._file = file
        if contents is None:
            self._contents, self._size = _load_file_contents(self._file, size)
        else:
            self._contents, self._size = (contents, size)

    def __eq__(self, other):
        # Quick optimization:
        if (isinstance(other, FilePackIndex) and
            self._fan_out_table != other._fan_out_table):
            return False

        return super(FilePackIndex, self).__eq__(other)

    def close(self):
        self._file.close()
        if getattr(self._contents, "close", None) is not None:
            self._contents.close()

    def __len__(self):
        """Return the number of entries in this pack index."""
        return self._fan_out_table[-1]

    def _unpack_entry(self, i):
        """Unpack the i-th entry in the index file.

        :return: Tuple with object name (SHA), offset in pack file and CRC32
            checksum (if known).
        """
        raise NotImplementedError(self._unpack_entry)

    def _unpack_name(self, i):
        """Unpack the i-th name from the index file."""
        raise NotImplementedError(self._unpack_name)

    def _unpack_offset(self, i):
        """Unpack the i-th object offset from the index file."""
        raise NotImplementedError(self._unpack_offset)

    def _unpack_crc32_checksum(self, i):
        """Unpack the crc32 checksum for the i-th object from the index file."""
        raise NotImplementedError(self._unpack_crc32_checksum)

    def _itersha(self):
        for i in range(len(self)):
            yield self._unpack_name(i)

    def iterentries(self):
        """Iterate over the entries in this pack index.

        :return: iterator over tuples with object name, offset in packfile and
            crc32 checksum.
        """
        for i in range(len(self)):
            yield self._unpack_entry(i)

    def _read_fan_out_table(self, start_offset):
        ret = []
        for i in range(0x100):
            fanout_entry = self._contents[start_offset+i*4:start_offset+(i+1)*4]
            ret.append(struct.unpack('>L', fanout_entry)[0])
        return ret

    def check(self):
        """Check that the stored checksum matches the actual checksum."""
        actual = self.calculate_checksum()
        stored = self.get_stored_checksum()
        if actual != stored:
            raise ChecksumMismatch(stored, actual)

    def calculate_checksum(self):
        """Calculate the SHA1 checksum over this pack index.

        :return: This is a 20-byte binary digest
        """
        return make_sha(self._contents[:-20]).digest()

    def get_pack_checksum(self):
        """Return the SHA1 checksum stored for the corresponding packfile.

        :return: 20-byte binary digest
        """
        return str(self._contents[-40:-20])

    def get_stored_checksum(self):
        """Return the SHA1 checksum stored for this index.

        :return: 20-byte binary digest
        """
        return str(self._contents[-20:])

    def _object_index(self, sha):
        """See object_index.

        :param sha: A *binary* SHA string. (20 characters long)_
        """
        assert len(sha) == 20
        idx = ord(sha[0])
        if idx == 0:
            start = 0
        else:
            start = self._fan_out_table[idx-1]
        end = self._fan_out_table[idx]
        i = bisect_find_sha(start, end, sha, self._unpack_name)
        if i is None:
            raise KeyError(sha)
        return self._unpack_offset(i)


class PackIndex1(FilePackIndex):
    """Version 1 Pack Index file."""

    def __init__(self, filename, file=None, contents=None, size=None):
        super(PackIndex1, self).__init__(filename, file, contents, size)
        self.version = 1
        self._fan_out_table = self._read_fan_out_table(0)

    def _unpack_entry(self, i):
        (offset, name) = unpack_from('>L20s', self._contents,
                                     (0x100 * 4) + (i * 24))
        return (name, offset, None)

    def _unpack_name(self, i):
        offset = (0x100 * 4) + (i * 24) + 4
        return self._contents[offset:offset+20]

    def _unpack_offset(self, i):
        offset = (0x100 * 4) + (i * 24)
        return unpack_from('>L', self._contents, offset)[0]

    def _unpack_crc32_checksum(self, i):
        # Not stored in v1 index files
        return None


class PackIndex2(FilePackIndex):
    """Version 2 Pack Index file."""

    def __init__(self, filename, file=None, contents=None, size=None):
        super(PackIndex2, self).__init__(filename, file, contents, size)
        if self._contents[:4] != '\377tOc':
            raise AssertionError('Not a v2 pack index file')
        (self.version, ) = unpack_from('>L', self._contents, 4)
        if self.version != 2:
            raise AssertionError('Version was %d' % self.version)
        self._fan_out_table = self._read_fan_out_table(8)
        self._name_table_offset = 8 + 0x100 * 4
        self._crc32_table_offset = self._name_table_offset + 20 * len(self)
        self._pack_offset_table_offset = (self._crc32_table_offset +
                                          4 * len(self))
        self._pack_offset_largetable_offset = (self._pack_offset_table_offset +
                                          4 * len(self))

    def _unpack_entry(self, i):
        return (self._unpack_name(i), self._unpack_offset(i),
                self._unpack_crc32_checksum(i))

    def _unpack_name(self, i):
        offset = self._name_table_offset + i * 20
        return self._contents[offset:offset+20]

    def _unpack_offset(self, i):
        offset = self._pack_offset_table_offset + i * 4
        offset = unpack_from('>L', self._contents, offset)[0]
        if offset & (2**31):
            offset = self._pack_offset_largetable_offset + (offset&(2**31-1)) * 8L
            offset = unpack_from('>Q', self._contents, offset)[0]
        return offset

    def _unpack_crc32_checksum(self, i):
        return unpack_from('>L', self._contents,
                          self._crc32_table_offset + i * 4)[0]


def read_pack_header(read):
    """Read the header of a pack file.

    :param read: Read function
    :return: Tuple of (pack version, number of objects). If no data is available
        to read, returns (None, None).
    """
    header = read(12)
    if not header:
        return None, None
    if header[:4] != 'PACK':
        raise AssertionError('Invalid pack header %r' % header)
    (version,) = unpack_from('>L', header, 4)
    if version not in (2, 3):
        raise AssertionError('Version was %d' % version)
    (num_objects,) = unpack_from('>L', header, 8)
    return (version, num_objects)


def chunks_length(chunks):
    return sum(imap(len, chunks))


def unpack_object(read_all, read_some=None, compute_crc32=False,
                  include_comp=False, zlib_bufsize=_ZLIB_BUFSIZE):
    """Unpack a Git object.

    :param read_all: Read function that blocks until the number of requested
        bytes are read.
    :param read_some: Read function that returns at least one byte, but may not
        return the number of bytes requested.
    :param compute_crc32: If True, compute the CRC32 of the compressed data. If
        False, the returned CRC32 will be None.
    :param include_comp: If True, include compressed data in the result.
    :param zlib_bufsize: An optional buffer size for zlib operations.
    :return: A tuple of (unpacked, unused), where unused is the unused data
        leftover from decompression, and unpacked in an UnpackedObject with
        the following attrs set:

        * obj_chunks     (for non-delta types)
        * pack_type_num
        * delta_base     (for delta types)
        * comp_chunks    (if include_comp is True)
        * decomp_chunks
        * decomp_len
        * crc32          (if compute_crc32 is True)
    """
    if read_some is None:
        read_some = read_all
    if compute_crc32:
        crc32 = 0
    else:
        crc32 = None

    bytes, crc32 = take_msb_bytes(read_all, crc32=crc32)
    type_num = (bytes[0] >> 4) & 0x07
    size = bytes[0] & 0x0f
    for i, byte in enumerate(bytes[1:]):
        size += (byte & 0x7f) << ((i * 7) + 4)

    raw_base = len(bytes)
    if type_num == OFS_DELTA:
        bytes, crc32 = take_msb_bytes(read_all, crc32=crc32)
        raw_base += len(bytes)
        if bytes[-1] & 0x80:
            raise AssertionError
        delta_base_offset = bytes[0] & 0x7f
        for byte in bytes[1:]:
            delta_base_offset += 1
            delta_base_offset <<= 7
            delta_base_offset += (byte & 0x7f)
        delta_base = delta_base_offset
    elif type_num == REF_DELTA:
        delta_base = read_all(20)
        if compute_crc32:
            crc32 = binascii.crc32(delta_base, crc32)
        raw_base += 20
    else:
        delta_base = None

    unpacked = UnpackedObject(type_num, delta_base, size, crc32)
    unused = read_zlib_chunks(read_some, unpacked, buffer_size=zlib_bufsize,
                              include_comp=include_comp)
    return unpacked, unused


def _compute_object_size((num, obj)):
    """Compute the size of a unresolved object for use with LRUSizeCache."""
    if num in DELTA_TYPES:
        return chunks_length(obj[1])
    return chunks_length(obj)


class PackStreamReader(object):
    """Class to read a pack stream.

    The pack is read from a ReceivableProtocol using read() or recv() as
    appropriate.
    """

    def __init__(self, read_all, read_some=None, zlib_bufsize=_ZLIB_BUFSIZE):
        self.read_all = read_all
        if read_some is None:
            self.read_some = read_all
        else:
            self.read_some = read_some
        self.sha = make_sha()
        self._offset = 0
        self._rbuf = StringIO()
        # trailer is a deque to avoid memory allocation on small reads
        self._trailer = deque()
        self._zlib_bufsize = zlib_bufsize

    def _read(self, read, size):
        """Read up to size bytes using the given callback.

        As a side effect, update the verifier's hash (excluding the last 20
        bytes read).

        :param read: The read callback to read from.
        :param size: The maximum number of bytes to read; the particular
            behavior is callback-specific.
        """
        data = read(size)

        # maintain a trailer of the last 20 bytes we've read
        n = len(data)
        self._offset += n
        tn = len(self._trailer)
        if n >= 20:
            to_pop = tn
            to_add = 20
        else:
            to_pop = max(n + tn - 20, 0)
            to_add = n
        for _ in xrange(to_pop):
            self.sha.update(self._trailer.popleft())
        self._trailer.extend(data[-to_add:])

        # hash everything but the trailer
        self.sha.update(data[:-to_add])
        return data

    def _buf_len(self):
        buf = self._rbuf
        start = buf.tell()
        buf.seek(0, SEEK_END)
        end = buf.tell()
        buf.seek(start)
        return end - start

    @property
    def offset(self):
        return self._offset - self._buf_len()

    def read(self, size):
        """Read, blocking until size bytes are read."""
        buf_len = self._buf_len()
        if buf_len >= size:
            return self._rbuf.read(size)
        buf_data = self._rbuf.read()
        self._rbuf = StringIO()
        return buf_data + self._read(self.read_all, size - buf_len)

    def recv(self, size):
        """Read up to size bytes, blocking until one byte is read."""
        buf_len = self._buf_len()
        if buf_len:
            data = self._rbuf.read(size)
            if size >= buf_len:
                self._rbuf = StringIO()
            return data
        return self._read(self.read_some, size)

    def __len__(self):
        return self._num_objects

    def read_objects(self, compute_crc32=False):
        """Read the objects in this pack file.

        :param compute_crc32: If True, compute the CRC32 of the compressed
            data. If False, the returned CRC32 will be None.
        :return: Iterator over UnpackedObjects with the following members set:
            offset
            obj_type_num
            obj_chunks (for non-delta types)
            delta_base (for delta types)
            decomp_chunks
            decomp_len
            crc32 (if compute_crc32 is True)
        :raise ChecksumMismatch: if the checksum of the pack contents does not
            match the checksum in the pack trailer.
        :raise zlib.error: if an error occurred during zlib decompression.
        :raise IOError: if an error occurred writing to the output file.
        """
        pack_version, self._num_objects = read_pack_header(self.read)
        if pack_version is None:
            return

        for i in xrange(self._num_objects):
            offset = self.offset
            unpacked, unused = unpack_object(
              self.read, read_some=self.recv, compute_crc32=compute_crc32,
              zlib_bufsize=self._zlib_bufsize)
            unpacked.offset = offset

            # prepend any unused data to current read buffer
            buf = StringIO()
            buf.write(unused)
            buf.write(self._rbuf.read())
            buf.seek(0)
            self._rbuf = buf

            yield unpacked

        if self._buf_len() < 20:
            # If the read buffer is full, then the last read() got the whole
            # trailer off the wire. If not, it means there is still some of the
            # trailer to read. We need to read() all 20 bytes; N come from the
            # read buffer and (20 - N) come from the wire.
            self.read(20)

        pack_sha = ''.join(self._trailer)
        if pack_sha != self.sha.digest():
            raise ChecksumMismatch(sha_to_hex(pack_sha), self.sha.hexdigest())


class PackStreamCopier(PackStreamReader):
    """Class to verify a pack stream as it is being read.

    The pack is read from a ReceivableProtocol using read() or recv() as
    appropriate and written out to the given file-like object.
    """

    def __init__(self, read_all, read_some, outfile, delta_iter=None):
        """Initialize the copier.

        :param read_all: Read function that blocks until the number of requested
            bytes are read.
        :param read_some: Read function that returns at least one byte, but may
            not return the number of bytes requested.
        :param outfile: File-like object to write output through.
        :param delta_iter: Optional DeltaChainIterator to record deltas as we
            read them.
        """
        super(PackStreamCopier, self).__init__(read_all, read_some=read_some)
        self.outfile = outfile
        self._delta_iter = delta_iter

    def _read(self, read, size):
        """Read data from the read callback and write it to the file."""
        data = super(PackStreamCopier, self)._read(read, size)
        self.outfile.write(data)
        return data

    def verify(self):
        """Verify a pack stream and write it to the output file.

        See PackStreamReader.iterobjects for a list of exceptions this may
        throw.
        """
        if self._delta_iter:
            for unpacked in self.read_objects():
                self._delta_iter.record(unpacked)
        else:
            for _ in self.read_objects():
                pass


def obj_sha(type, chunks):
    """Compute the SHA for a numeric type and object chunks."""
    sha = make_sha()
    sha.update(object_header(type, chunks_length(chunks)))
    for chunk in chunks:
        sha.update(chunk)
    return sha.digest()


def compute_file_sha(f, start_ofs=0, end_ofs=0, buffer_size=1<<16):
    """Hash a portion of a file into a new SHA.

    :param f: A file-like object to read from that supports seek().
    :param start_ofs: The offset in the file to start reading at.
    :param end_ofs: The offset in the file to end reading at, relative to the
        end of the file.
    :param buffer_size: A buffer size for reading.
    :return: A new SHA object updated with data read from the file.
    """
    sha = make_sha()
    f.seek(0, SEEK_END)
    todo = f.tell() + end_ofs - start_ofs
    f.seek(start_ofs)
    while todo:
        data = f.read(min(todo, buffer_size))
        sha.update(data)
        todo -= len(data)
    return sha


class PackData(object):
    """The data contained in a packfile.

    Pack files can be accessed both sequentially for exploding a pack, and
    directly with the help of an index to retrieve a specific object.

    The objects within are either complete or a delta aginst another.

    The header is variable length. If the MSB of each byte is set then it
    indicates that the subsequent byte is still part of the header.
    For the first byte the next MS bits are the type, which tells you the type
    of object, and whether it is a delta. The LS byte is the lowest bits of the
    size. For each subsequent byte the LS 7 bits are the next MS bits of the
    size, i.e. the last byte of the header contains the MS bits of the size.

    For the complete objects the data is stored as zlib deflated data.
    The size in the header is the uncompressed object size, so to uncompress
    you need to just keep feeding data to zlib until you get an object back,
    or it errors on bad data. This is done here by just giving the complete
    buffer from the start of the deflated object on. This is bad, but until I
    get mmap sorted out it will have to do.

    Currently there are no integrity checks done. Also no attempt is made to
    try and detect the delta case, or a request for an object at the wrong
    position.  It will all just throw a zlib or KeyError.
    """

    def __init__(self, filename, file=None, size=None):
        """Create a PackData object representing the pack in the given filename.

        The file must exist and stay readable until the object is disposed of. It
        must also stay the same size. It will be mapped whenever needed.

        Currently there is a restriction on the size of the pack as the python
        mmap implementation is flawed.
        """
        self._filename = filename
        self._size = size
        self._header_size = 12
        if file is None:
            self._file = GitFile(self._filename, 'rb')
        else:
            self._file = file
        (version, self._num_objects) = read_pack_header(self._file.read)
        self._offset_cache = LRUSizeCache(1024*1024*20,
            compute_size=_compute_object_size)
        self.pack = None

    @classmethod
    def from_file(cls, file, size):
        return cls(str(file), file=file, size=size)

    @classmethod
    def from_path(cls, path):
        return cls(filename=path)

    def close(self):
        self._file.close()

    def _get_size(self):
        if self._size is not None:
            return self._size
        self._size = os.path.getsize(self._filename)
        if self._size < self._header_size:
            errmsg = ('%s is too small for a packfile (%d < %d)' %
                      (self._filename, self._size, self._header_size))
            raise AssertionError(errmsg)
        return self._size

    def __len__(self):
        """Returns the number of objects in this pack."""
        return self._num_objects

    def calculate_checksum(self):
        """Calculate the checksum for this pack.

        :return: 20-byte binary SHA1 digest
        """
        return compute_file_sha(self._file, end_ofs=-20).digest()

    def get_ref(self, sha):
        """Get the object for a ref SHA, only looking in this pack."""
        # TODO: cache these results
        if self.pack is None:
            raise KeyError(sha)
        try:
            offset = self.pack.index.object_index(sha)
        except KeyError:
            offset = None
        if offset:
            type, obj = self.get_object_at(offset)
        elif self.pack is not None and self.pack.resolve_ext_ref:
            type, obj = self.pack.resolve_ext_ref(sha)
        else:
            raise KeyError(sha)
        return offset, type, obj

    def resolve_object(self, offset, type, obj, get_ref=None):
        """Resolve an object, possibly resolving deltas when necessary.

        :return: Tuple with object type and contents.
        """
        if type not in DELTA_TYPES:
            return type, obj

        if get_ref is None:
            get_ref = self.get_ref
        if type == OFS_DELTA:
            (delta_offset, delta) = obj
            # TODO: clean up asserts and replace with nicer error messages
            assert isinstance(offset, int) or isinstance(offset, long)
            assert isinstance(delta_offset, int) or isinstance(offset, long)
            base_offset = offset-delta_offset
            type, base_obj = self.get_object_at(base_offset)
            assert isinstance(type, int)
        elif type == REF_DELTA:
            (basename, delta) = obj
            assert isinstance(basename, str) and len(basename) == 20
            base_offset, type, base_obj = get_ref(basename)
            assert isinstance(type, int)
        type, base_chunks = self.resolve_object(base_offset, type, base_obj)
        chunks = apply_delta(base_chunks, delta)
        # TODO(dborowitz): This can result in poor performance if large base
        # objects are separated from deltas in the pack. We should reorganize
        # so that we apply deltas to all objects in a chain one after the other
        # to optimize cache performance.
        if offset is not None:
            self._offset_cache[offset] = type, chunks
        return type, chunks

    def iterobjects(self, progress=None, compute_crc32=True):
        self._file.seek(self._header_size)
        for i in xrange(1, self._num_objects + 1):
            offset = self._file.tell()
            unpacked, unused = unpack_object(
              self._file.read, compute_crc32=compute_crc32)
            if progress is not None:
                progress(i, self._num_objects)
            yield (offset, unpacked.pack_type_num, unpacked._obj(),
                   unpacked.crc32)
            self._file.seek(-len(unused), SEEK_CUR)  # Back up over unused data.

    def _iter_unpacked(self):
        # TODO(dborowitz): Merge this with iterobjects, if we can change its
        # return type.
        self._file.seek(self._header_size)
        for _ in xrange(self._num_objects):
            offset = self._file.tell()
            unpacked, unused = unpack_object(
              self._file.read, compute_crc32=False)
            unpacked.offset = offset
            yield unpacked
            self._file.seek(-len(unused), SEEK_CUR)  # Back up over unused data.

    def iterentries(self, progress=None):
        """Yield entries summarizing the contents of this pack.

        :param progress: Progress function, called with current and total
            object count.
        :return: iterator of tuples with (sha, offset, crc32)
        """
        num_objects = self._num_objects
        resolve_ext_ref = (
            self.pack.resolve_ext_ref if self.pack is not None else None)
        indexer = PackIndexer.for_pack_data(
            self, resolve_ext_ref=resolve_ext_ref)
        for i, result in enumerate(indexer):
            if progress is not None:
                progress(i, num_objects)
            yield result

    def sorted_entries(self, progress=None):
        """Return entries in this pack, sorted by SHA.

        :param progress: Progress function, called with current and total
            object count
        :return: List of tuples with (sha, offset, crc32)
        """
        ret = list(self.iterentries(progress=progress))
        ret.sort()
        return ret

    def create_index_v1(self, filename, progress=None):
        """Create a version 1 file for this data file.

        :param filename: Index filename.
        :param progress: Progress report function
        :return: Checksum of index file
        """
        entries = self.sorted_entries(progress=progress)
        f = GitFile(filename, 'wb')
        try:
            return write_pack_index_v1(f, entries, self.calculate_checksum())
        finally:
            f.close()

    def create_index_v2(self, filename, progress=None):
        """Create a version 2 index file for this data file.

        :param filename: Index filename.
        :param progress: Progress report function
        :return: Checksum of index file
        """
        entries = self.sorted_entries(progress=progress)
        f = GitFile(filename, 'wb')
        try:
            return write_pack_index_v2(f, entries, self.calculate_checksum())
        finally:
            f.close()

    def create_index(self, filename, progress=None,
                     version=2):
        """Create an  index file for this data file.

        :param filename: Index filename.
        :param progress: Progress report function
        :return: Checksum of index file
        """
        if version == 1:
            return self.create_index_v1(filename, progress)
        elif version == 2:
            return self.create_index_v2(filename, progress)
        else:
            raise ValueError('unknown index format %d' % version)

    def get_stored_checksum(self):
        """Return the expected checksum stored in this pack."""
        self._file.seek(-20, SEEK_END)
        return self._file.read(20)

    def check(self):
        """Check the consistency of this pack."""
        actual = self.calculate_checksum()
        stored = self.get_stored_checksum()
        if actual != stored:
            raise ChecksumMismatch(stored, actual)

    def get_object_at(self, offset):
        """Given an offset in to the packfile return the object that is there.

        Using the associated index the location of an object can be looked up,
        and then the packfile can be asked directly for that object using this
        function.
        """
        if offset in self._offset_cache:
            return self._offset_cache[offset]
        assert isinstance(offset, long) or isinstance(offset, int),\
                'offset was %r' % offset
        assert offset >= self._header_size
        self._file.seek(offset)
        unpacked, _ = unpack_object(self._file.read)
        return (unpacked.pack_type_num, unpacked._obj())


class DeltaChainIterator(object):
    """Abstract iterator over pack data based on delta chains.

    Each object in the pack is guaranteed to be inflated exactly once,
    regardless of how many objects reference it as a delta base. As a result,
    memory usage is proportional to the length of the longest delta chain.

    Subclasses can override _result to define the result type of the iterator.
    By default, results are UnpackedObjects with the following members set:

    * offset
    * obj_type_num
    * obj_chunks
    * pack_type_num
    * delta_base     (for delta types)
    * comp_chunks    (if _include_comp is True)
    * decomp_chunks
    * decomp_len
    * crc32          (if _compute_crc32 is True)
    """

    _compute_crc32 = False
    _include_comp = False

    def __init__(self, file_obj, resolve_ext_ref=None):
        self._file = file_obj
        self._resolve_ext_ref = resolve_ext_ref
        self._pending_ofs = defaultdict(list)
        self._pending_ref = defaultdict(list)
        self._full_ofs = []
        self._shas = {}
        self._ext_refs = []

    @classmethod
    def for_pack_data(cls, pack_data, resolve_ext_ref=None):
        walker = cls(None, resolve_ext_ref=resolve_ext_ref)
        walker.set_pack_data(pack_data)
        for unpacked in pack_data._iter_unpacked():
            walker.record(unpacked)
        return walker

    def record(self, unpacked):
        type_num = unpacked.pack_type_num
        offset = unpacked.offset
        if type_num == OFS_DELTA:
            base_offset = offset - unpacked.delta_base
            self._pending_ofs[base_offset].append(offset)
        elif type_num == REF_DELTA:
            self._pending_ref[unpacked.delta_base].append(offset)
        else:
            self._full_ofs.append((offset, type_num))

    def set_pack_data(self, pack_data):
        self._file = pack_data._file

    def _walk_all_chains(self):
        for offset, type_num in self._full_ofs:
            for result in self._follow_chain(offset, type_num, None):
                yield result
        for result in self._walk_ref_chains():
            yield result
        assert not self._pending_ofs

    def _ensure_no_pending(self):
        if self._pending_ref:
            raise KeyError([sha_to_hex(s) for s in self._pending_ref])

    def _walk_ref_chains(self):
        if not self._resolve_ext_ref:
            self._ensure_no_pending()
            return

        for base_sha, pending in sorted(self._pending_ref.iteritems()):
            try:
                type_num, chunks = self._resolve_ext_ref(base_sha)
            except KeyError:
                # Not an external ref, but may depend on one. Either it will get
                # popped via a _follow_chain call, or we will raise an error
                # below.
                continue
            self._ext_refs.append(base_sha)
            self._pending_ref.pop(base_sha)
            for new_offset in pending:
                for result in self._follow_chain(new_offset, type_num, chunks):
                    yield result

        self._ensure_no_pending()

    def _result(self, unpacked):
        return unpacked

    def _resolve_object(self, offset, obj_type_num, base_chunks):
        self._file.seek(offset)
        unpacked, _ = unpack_object(
          self._file.read, include_comp=self._include_comp,
          compute_crc32=self._compute_crc32)
        unpacked.offset = offset
        if base_chunks is None:
            assert unpacked.pack_type_num == obj_type_num
        else:
            assert unpacked.pack_type_num in DELTA_TYPES
            unpacked.obj_type_num = obj_type_num
            unpacked.obj_chunks = apply_delta(base_chunks,
                                              unpacked.decomp_chunks)
        return unpacked

    def _follow_chain(self, offset, obj_type_num, base_chunks):
        # Unlike PackData.get_object_at, there is no need to cache offsets as
        # this approach by design inflates each object exactly once.
        unpacked = self._resolve_object(offset, obj_type_num, base_chunks)
        yield self._result(unpacked)

        pending = chain(self._pending_ofs.pop(unpacked.offset, []),
                        self._pending_ref.pop(unpacked.sha(), []))
        for new_offset in pending:
            for new_result in self._follow_chain(
              new_offset, unpacked.obj_type_num, unpacked.obj_chunks):
                yield new_result

    def __iter__(self):
        return self._walk_all_chains()

    def ext_refs(self):
        return self._ext_refs


class PackIndexer(DeltaChainIterator):
    """Delta chain iterator that yields index entries."""

    _compute_crc32 = True

    def _result(self, unpacked):
        return unpacked.sha(), unpacked.offset, unpacked.crc32


class PackInflater(DeltaChainIterator):
    """Delta chain iterator that yields ShaFile objects."""

    def _result(self, unpacked):
        return unpacked.sha_file()


class SHA1Reader(object):
    """Wrapper around a file-like object that remembers the SHA1 of its data."""

    def __init__(self, f):
        self.f = f
        self.sha1 = make_sha('')

    def read(self, num=None):
        data = self.f.read(num)
        self.sha1.update(data)
        return data

    def check_sha(self):
        stored = self.f.read(20)
        if stored != self.sha1.digest():
            raise ChecksumMismatch(self.sha1.hexdigest(), sha_to_hex(stored))

    def close(self):
        return self.f.close()

    def tell(self):
        return self.f.tell()


class SHA1Writer(object):
    """Wrapper around a file-like object that remembers the SHA1 of its data."""

    def __init__(self, f):
        self.f = f
        self.length = 0
        self.sha1 = make_sha('')

    def write(self, data):
        self.sha1.update(data)
        self.f.write(data)
        self.length += len(data)

    def write_sha(self):
        sha = self.sha1.digest()
        assert len(sha) == 20
        self.f.write(sha)
        self.length += len(sha)
        return sha

    def close(self):
        sha = self.write_sha()
        self.f.close()
        return sha

    def offset(self):
        return self.length

    def tell(self):
        return self.f.tell()


def pack_object_header(type_num, delta_base, size):
    """Create a pack object header for the given object info.

    :param type_num: Numeric type of the object.
    :param delta_base: Delta base offset or ref, or None for whole objects.
    :param size: Uncompressed object size.
    :return: A header for a packed object.
    """
    header = ''
    c = (type_num << 4) | (size & 15)
    size >>= 4
    while size:
        header += (chr(c | 0x80))
        c = size & 0x7f
        size >>= 7
    header += chr(c)
    if type_num == OFS_DELTA:
        ret = [delta_base & 0x7f]
        delta_base >>= 7
        while delta_base:
            delta_base -= 1
            ret.insert(0, 0x80 | (delta_base & 0x7f))
            delta_base >>= 7
        header += ''.join([chr(x) for x in ret])
    elif type_num == REF_DELTA:
        assert len(delta_base) == 20
        header += delta_base
    return header


def write_pack_object(f, type, object, sha=None):
    """Write pack object to a file.

    :param f: File to write to
    :param type: Numeric type of the object
    :param object: Object to write
    :return: Tuple with offset at which the object was written, and crc32
    """
    if type in DELTA_TYPES:
        delta_base, object = object
    else:
        delta_base = None
    header = pack_object_header(type, delta_base, len(object))
    comp_data = zlib.compress(object)
    crc32 = 0
    for data in (header, comp_data):
        f.write(data)
        if sha is not None:
            sha.update(data)
        crc32 = binascii.crc32(data, crc32)
    return crc32 & 0xffffffff


def write_pack(filename, objects, num_objects=None):
    """Write a new pack data file.

    :param filename: Path to the new pack file (without .pack extension)
    :param objects: Iterable of (object, path) tuples to write.
        Should provide __len__
    :return: Tuple with checksum of pack file and index file
    """
    if num_objects is not None:
        warnings.warn('num_objects argument to write_pack is deprecated',
                      DeprecationWarning)
    f = GitFile(filename + '.pack', 'wb')
    try:
        entries, data_sum = write_pack_objects(f, objects,
            num_objects=num_objects)
    finally:
        f.close()
    entries = [(k, v[0], v[1]) for (k, v) in entries.iteritems()]
    entries.sort()
    f = GitFile(filename + '.idx', 'wb')
    try:
        return data_sum, write_pack_index_v2(f, entries, data_sum)
    finally:
        f.close()


def write_pack_header(f, num_objects):
    """Write a pack header for the given number of objects."""
    f.write('PACK')                          # Pack header
    f.write(struct.pack('>L', 2))            # Pack version
    f.write(struct.pack('>L', num_objects))  # Number of objects in pack


def deltify_pack_objects(objects, window=10):
    """Generate deltas for pack objects.

    :param objects: Objects to deltify
    :param window: Window size
    :return: Iterator over type_num, object id, delta_base, content
        delta_base is None for full text entries
    """
    # Build a list of objects ordered by the magic Linus heuristic
    # This helps us find good objects to diff against us
    magic = []
    for obj, path in objects:
        magic.append((obj.type_num, path, -obj.raw_length(), obj))
    magic.sort()

    possible_bases = deque()

    for type_num, path, neg_length, o in magic:
        raw = o.as_raw_string()
        winner = raw
        winner_base = None
        for base in possible_bases:
            if base.type_num != type_num:
                continue
            delta = create_delta(base.as_raw_string(), raw)
            if len(delta) < len(winner):
                winner_base = base.sha().digest()
                winner = delta
        yield type_num, o.sha().digest(), winner_base, winner
        possible_bases.appendleft(o)
        while len(possible_bases) > window:
            possible_bases.pop()


def write_pack_objects(f, objects, window=10, num_objects=None):
    """Write a new pack data file.

    :param f: File to write to
    :param objects: Iterable of (object, path) tuples to write.
        Should provide __len__
    :param window: Sliding window size for searching for deltas; currently
                   unimplemented
    :param num_objects: Number of objects (do not use, deprecated)
    :return: Dict mapping id -> (offset, crc32 checksum), pack checksum
    """
    if num_objects is None:
        num_objects = len(objects)
    # FIXME: pack_contents = deltify_pack_objects(objects, window)
    pack_contents = (
        (o.type_num, o.sha().digest(), None, o.as_raw_string())
        for (o, path) in objects)
    return write_pack_data(f, num_objects, pack_contents)


def write_pack_data(f, num_records, records):
    """Write a new pack data file.

    :param f: File to write to
    :param num_records: Number of records
    :param records: Iterator over type_num, object_id, delta_base, raw
    :return: Dict mapping id -> (offset, crc32 checksum), pack checksum
    """
    # Write the pack
    entries = {}
    f = SHA1Writer(f)
    write_pack_header(f, num_records)
    for type_num, object_id, delta_base, raw in records:
        if delta_base is not None:
            try:
                base_offset, base_crc32 = entries[delta_base]
            except KeyError:
                type_num = REF_DELTA
                raw = (delta_base, raw)
            else:
                type_num = OFS_DELTA
                raw = (base_offset, raw)
        offset = f.offset()
        crc32 = write_pack_object(f, type_num, raw)
        entries[object_id] = (offset, crc32)
    return entries, f.write_sha()


def write_pack_index_v1(f, entries, pack_checksum):
    """Write a new pack index file.

    :param f: A file-like object to write to
    :param entries: List of tuples with object name (sha), offset_in_pack,
        and crc32_checksum.
    :param pack_checksum: Checksum of the pack file.
    :return: The SHA of the written index file
    """
    f = SHA1Writer(f)
    fan_out_table = defaultdict(lambda: 0)
    for (name, offset, entry_checksum) in entries:
        fan_out_table[ord(name[0])] += 1
    # Fan-out table
    for i in range(0x100):
        f.write(struct.pack('>L', fan_out_table[i]))
        fan_out_table[i+1] += fan_out_table[i]
    for (name, offset, entry_checksum) in entries:
        if not (offset <= 0xffffffff):
            raise TypeError("pack format 1 only supports offsets < 2Gb")
        f.write(struct.pack('>L20s', offset, name))
    assert len(pack_checksum) == 20
    f.write(pack_checksum)
    return f.write_sha()


def create_delta(base_buf, target_buf):
    """Use python difflib to work out how to transform base_buf to target_buf.

    :param base_buf: Base buffer
    :param target_buf: Target buffer
    """
    assert isinstance(base_buf, str)
    assert isinstance(target_buf, str)
    out_buf = ''
    # write delta header
    def encode_size(size):
        ret = ''
        c = size & 0x7f
        size >>= 7
        while size:
            ret += chr(c | 0x80)
            c = size & 0x7f
            size >>= 7
        ret += chr(c)
        return ret
    out_buf += encode_size(len(base_buf))
    out_buf += encode_size(len(target_buf))
    # write out delta opcodes
    seq = difflib.SequenceMatcher(a=base_buf, b=target_buf)
    for opcode, i1, i2, j1, j2 in seq.get_opcodes():
        # Git patch opcodes don't care about deletes!
        #if opcode == 'replace' or opcode == 'delete':
        #    pass
        if opcode == 'equal':
            # If they are equal, unpacker will use data from base_buf
            # Write out an opcode that says what range to use
            scratch = ''
            op = 0x80
            o = i1
            for i in range(4):
                if o & 0xff << i*8:
                    scratch += chr((o >> i*8) & 0xff)
                    op |= 1 << i
            s = i2 - i1
            for i in range(2):
                if s & 0xff << i*8:
                    scratch += chr((s >> i*8) & 0xff)
                    op |= 1 << (4+i)
            out_buf += chr(op)
            out_buf += scratch
        if opcode == 'replace' or opcode == 'insert':
            # If we are replacing a range or adding one, then we just
            # output it to the stream (prefixed by its size)
            s = j2 - j1
            o = j1
            while s > 127:
                out_buf += chr(127)
                out_buf += target_buf[o:o+127]
                s -= 127
                o += 127
            out_buf += chr(s)
            out_buf += target_buf[o:o+s]
    return out_buf


def apply_delta(src_buf, delta):
    """Based on the similar function in git's patch-delta.c.

    :param src_buf: Source buffer
    :param delta: Delta instructions
    """
    if type(src_buf) != str:
        src_buf = ''.join(src_buf)
    if type(delta) != str:
        delta = ''.join(delta)
    out = []
    index = 0
    delta_length = len(delta)
    def get_delta_header_size(delta, index):
        size = 0
        i = 0
        while delta:
            cmd = ord(delta[index])
            index += 1
            size |= (cmd & ~0x80) << i
            i += 7
            if not cmd & 0x80:
                break
        return size, index
    src_size, index = get_delta_header_size(delta, index)
    dest_size, index = get_delta_header_size(delta, index)
    assert src_size == len(src_buf), '%d vs %d' % (src_size, len(src_buf))
    while index < delta_length:
        cmd = ord(delta[index])
        index += 1
        if cmd & 0x80:
            cp_off = 0
            for i in range(4):
                if cmd & (1 << i):
                    x = ord(delta[index])
                    index += 1
                    cp_off |= x << (i * 8)
            cp_size = 0
            for i in range(3):
                if cmd & (1 << (4+i)):
                    x = ord(delta[index])
                    index += 1
                    cp_size |= x << (i * 8)
            if cp_size == 0:
                cp_size = 0x10000
            if (cp_off + cp_size < cp_size or
                cp_off + cp_size > src_size or
                cp_size > dest_size):
                break
            out.append(src_buf[cp_off:cp_off+cp_size])
        elif cmd != 0:
            out.append(delta[index:index+cmd])
            index += cmd
        else:
            raise ApplyDeltaError('Invalid opcode 0')

    if index != delta_length:
        raise ApplyDeltaError('delta not empty: %r' % delta[index:])

    if dest_size != chunks_length(out):
        raise ApplyDeltaError('dest size incorrect')

    return out


def write_pack_index_v2(f, entries, pack_checksum):
    """Write a new pack index file.

    :param f: File-like object to write to
    :param entries: List of tuples with object name (sha), offset_in_pack, and
        crc32_checksum.
    :param pack_checksum: Checksum of the pack file.
    :return: The SHA of the index file written
    """
    f = SHA1Writer(f)
    f.write('\377tOc') # Magic!
    f.write(struct.pack('>L', 2))
    fan_out_table = defaultdict(lambda: 0)
    for (name, offset, entry_checksum) in entries:
        fan_out_table[ord(name[0])] += 1
    # Fan-out table
    largetable = []
    for i in range(0x100):
        f.write(struct.pack('>L', fan_out_table[i]))
        fan_out_table[i+1] += fan_out_table[i]
    for (name, offset, entry_checksum) in entries:
        f.write(name)
    for (name, offset, entry_checksum) in entries:
        f.write(struct.pack('>L', entry_checksum))
    for (name, offset, entry_checksum) in entries:
        if offset < 2**31:
            f.write(struct.pack('>L', offset))
        else:
            f.write(struct.pack('>L', 2**31 + len(largetable)))
            largetable.append(offset)
    for offset in largetable:
        f.write(struct.pack('>Q', offset))
    assert len(pack_checksum) == 20
    f.write(pack_checksum)
    return f.write_sha()


class Pack(object):
    """A Git pack object."""

    def __init__(self, basename, resolve_ext_ref=None):
        self._basename = basename
        self._data = None
        self._idx = None
        self._idx_path = self._basename + '.idx'
        self._data_path = self._basename + '.pack'
        self._data_load = lambda: PackData(self._data_path)
        self._idx_load = lambda: load_pack_index(self._idx_path)
        self.resolve_ext_ref = resolve_ext_ref

    @classmethod
    def from_lazy_objects(self, data_fn, idx_fn):
        """Create a new pack object from callables to load pack data and
        index objects."""
        ret = Pack('')
        ret._data_load = data_fn
        ret._idx_load = idx_fn
        return ret

    @classmethod
    def from_objects(self, data, idx):
        """Create a new pack object from pack data and index objects."""
        ret = Pack('')
        ret._data_load = lambda: data
        ret._idx_load = lambda: idx
        return ret

    def name(self):
        """The SHA over the SHAs of the objects in this pack."""
        return self.index.objects_sha1()

    @property
    def data(self):
        """The pack data object being used."""
        if self._data is None:
            self._data = self._data_load()
            self._data.pack = self
            self.check_length_and_checksum()
        return self._data

    @property
    def index(self):
        """The index being used.

        :note: This may be an in-memory index
        """
        if self._idx is None:
            self._idx = self._idx_load()
        return self._idx

    def close(self):
        if self._data is not None:
            self._data.close()
        self.index.close()

    def __eq__(self, other):
        return type(self) == type(other) and self.index == other.index

    def __len__(self):
        """Number of entries in this pack."""
        return len(self.index)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._basename)

    def __iter__(self):
        """Iterate over all the sha1s of the objects in this pack."""
        return iter(self.index)

    def check_length_and_checksum(self):
        """Sanity check the length and checksum of the pack index and data."""
        assert len(self.index) == len(self.data)
        idx_stored_checksum = self.index.get_pack_checksum()
        data_stored_checksum = self.data.get_stored_checksum()
        if idx_stored_checksum != data_stored_checksum:
            raise ChecksumMismatch(sha_to_hex(idx_stored_checksum),
                                   sha_to_hex(data_stored_checksum))

    def check(self):
        """Check the integrity of this pack.

        :raise ChecksumMismatch: if a checksum for the index or data is wrong
        """
        self.index.check()
        self.data.check()
        for obj in self.iterobjects():
            obj.check()
        # TODO: object connectivity checks

    def get_stored_checksum(self):
        return self.data.get_stored_checksum()

    def __contains__(self, sha1):
        """Check whether this pack contains a particular SHA1."""
        try:
            self.index.object_index(sha1)
            return True
        except KeyError:
            return False

    def get_raw(self, sha1):
        offset = self.index.object_index(sha1)
        obj_type, obj = self.data.get_object_at(offset)
        type_num, chunks = self.data.resolve_object(offset, obj_type, obj)
        return type_num, ''.join(chunks)

    def __getitem__(self, sha1):
        """Retrieve the specified SHA1."""
        type, uncomp = self.get_raw(sha1)
        return ShaFile.from_raw_string(type, uncomp)

    def iterobjects(self):
        """Iterate over the objects in this pack."""
        return iter(PackInflater.for_pack_data(
            self.data, resolve_ext_ref=self.resolve_ext_ref))

    def pack_tuples(self):
        """Provide an iterable for use with write_pack_objects.

        :return: Object that can iterate over (object, path) tuples
            and provides __len__
        """
        class PackTupleIterable(object):

            def __init__(self, pack):
                self.pack = pack

            def __len__(self):
                return len(self.pack)

            def __iter__(self):
                return ((o, None) for o in self.pack.iterobjects())

        return PackTupleIterable(self)

    def keep(self, msg=None):
        """Add a .keep file for the pack, preventing git from garbage collecting it.

        :param msg: A message written inside the .keep file; can be used later to
                    determine whether or not a .keep file is obsolete.
        :return: The path of the .keep file, as a string.
        """
        keepfile_name = '%s.keep' % self._basename
        keepfile = GitFile(keepfile_name, 'wb')
        try:
            if msg:
                keepfile.write(msg)
                keepfile.write('\n')
        finally:
            keepfile.close()
        return keepfile_name


try:
    from dulwich._pack import apply_delta, bisect_find_sha
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = patch
# patch.py -- For dealing with packed-style patches.
# Copyright (C) 2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Classes for dealing with git am-style patches.

These patches are basically unified diffs with some extra metadata tacked
on.
"""

from difflib import SequenceMatcher
import rfc822
import time

from dulwich.objects import (
    Commit,
    S_ISGITLINK,
    )

FIRST_FEW_BYTES = 8000


def write_commit_patch(f, commit, contents, progress, version=None):
    """Write a individual file patch.

    :param commit: Commit object
    :param progress: Tuple with current patch number and total.
    :return: tuple with filename and contents
    """
    (num, total) = progress
    f.write("From %s %s\n" % (commit.id, time.ctime(commit.commit_time)))
    f.write("From: %s\n" % commit.author)
    f.write("Date: %s\n" % time.strftime("%a, %d %b %Y %H:%M:%S %Z"))
    f.write("Subject: [PATCH %d/%d] %s\n" % (num, total, commit.message))
    f.write("\n")
    f.write("---\n")
    try:
        import subprocess
        p = subprocess.Popen(["diffstat"], stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
    except (ImportError, OSError), e:
        pass # diffstat not available?
    else:
        (diffstat, _) = p.communicate(contents)
        f.write(diffstat)
        f.write("\n")
    f.write(contents)
    f.write("-- \n")
    if version is None:
        from dulwich import __version__ as dulwich_version
        f.write("Dulwich %d.%d.%d\n" % dulwich_version)
    else:
        f.write("%s\n" % version)


def get_summary(commit):
    """Determine the summary line for use in a filename.

    :param commit: Commit
    :return: Summary string
    """
    return commit.message.splitlines()[0].replace(" ", "-")


def unified_diff(a, b, fromfile='', tofile='', n=3):
    """difflib.unified_diff that doesn't write any dates or trailing spaces.

    Based on the same function in Python2.6.5-rc2's difflib.py
    """
    started = False
    for group in SequenceMatcher(None, a, b).get_grouped_opcodes(n):
        if not started:
            yield '--- %s\n' % fromfile
            yield '+++ %s\n' % tofile
            started = True
        i1, i2, j1, j2 = group[0][1], group[-1][2], group[0][3], group[-1][4]
        yield "@@ -%d,%d +%d,%d @@\n" % (i1+1, i2-i1, j1+1, j2-j1)
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in a[i1:i2]:
                    yield ' ' + line
                continue
            if tag == 'replace' or tag == 'delete':
                for line in a[i1:i2]:
                    if not line[-1] == '\n':
                        line += '\n\\ No newline at end of file\n'
                    yield '-' + line
            if tag == 'replace' or tag == 'insert':
                for line in b[j1:j2]:
                    if not line[-1] == '\n':
                        line += '\n\\ No newline at end of file\n'
                    yield '+' + line


def is_binary(content):
    """See if the first few bytes contain any null characters.

    :param content: Bytestring to check for binary content
    """
    return '\0' in content[:FIRST_FEW_BYTES]


def write_object_diff(f, store, (old_path, old_mode, old_id),
                                (new_path, new_mode, new_id),
                                diff_binary=False):
    """Write the diff for an object.

    :param f: File-like object to write to
    :param store: Store to retrieve objects from, if necessary
    :param (old_path, old_mode, old_hexsha): Old file
    :param (new_path, new_mode, new_hexsha): New file
    :param diff_binary: Whether to diff files even if they
        are considered binary files by is_binary().

    :note: the tuple elements should be None for nonexistant files
    """
    def shortid(hexsha):
        if hexsha is None:
            return "0" * 7
        else:
            return hexsha[:7]

    def content(mode, hexsha):
        if hexsha is None:
            return ''
        elif S_ISGITLINK(mode):
            return "Submodule commit " + hexsha + "\n"
        else:
            return store[hexsha].data

    def lines(content):
        if not content:
            return []
        else:
            return content.splitlines(True)

    if old_path is None:
        old_path = "/dev/null"
    else:
        old_path = "a/%s" % old_path
    if new_path is None:
        new_path = "/dev/null"
    else:
        new_path = "b/%s" % new_path
    f.write("diff --git %s %s\n" % (old_path, new_path))
    if old_mode != new_mode:
        if new_mode is not None:
            if old_mode is not None:
                f.write("old mode %o\n" % old_mode)
            f.write("new mode %o\n" % new_mode)
        else:
            f.write("deleted mode %o\n" % old_mode)
    f.write("index %s..%s" % (shortid(old_id), shortid(new_id)))
    if new_mode is not None:
        f.write(" %o" % new_mode)
    f.write("\n")
    old_content = content(old_mode, old_id)
    new_content = content(new_mode, new_id)
    if not diff_binary and (is_binary(old_content) or is_binary(new_content)):
        f.write("Binary files %s and %s differ\n" % (old_path, new_path))
    else:
        f.writelines(unified_diff(lines(old_content), lines(new_content),
            old_path, new_path))


def write_blob_diff(f, (old_path, old_mode, old_blob),
                       (new_path, new_mode, new_blob)):
    """Write diff file header.

    :param f: File-like object to write to
    :param (old_path, old_mode, old_blob): Previous file (None if nonexisting)
    :param (new_path, new_mode, new_blob): New file (None if nonexisting)

    :note: The use of write_object_diff is recommended over this function.
    """
    def blob_id(blob):
        if blob is None:
            return "0" * 7
        else:
            return blob.id[:7]
    def lines(blob):
        if blob is not None:
            return blob.data.splitlines(True)
        else:
            return []
    if old_path is None:
        old_path = "/dev/null"
    else:
        old_path = "a/%s" % old_path
    if new_path is None:
        new_path = "/dev/null"
    else:
        new_path = "b/%s" % new_path
    f.write("diff --git %s %s\n" % (old_path, new_path))
    if old_mode != new_mode:
        if new_mode is not None:
            if old_mode is not None:
                f.write("old mode %o\n" % old_mode)
            f.write("new mode %o\n" % new_mode)
        else:
            f.write("deleted mode %o\n" % old_mode)
    f.write("index %s..%s" % (blob_id(old_blob), blob_id(new_blob)))
    if new_mode is not None:
        f.write(" %o" % new_mode)
    f.write("\n")
    old_contents = lines(old_blob)
    new_contents = lines(new_blob)
    f.writelines(unified_diff(old_contents, new_contents,
        old_path, new_path))


def write_tree_diff(f, store, old_tree, new_tree, diff_binary=False):
    """Write tree diff.

    :param f: File-like object to write to.
    :param old_tree: Old tree id
    :param new_tree: New tree id
    :param diff_binary: Whether to diff files even if they
        are considered binary files by is_binary().
    """
    changes = store.tree_changes(old_tree, new_tree)
    for (oldpath, newpath), (oldmode, newmode), (oldsha, newsha) in changes:
        write_object_diff(f, store, (oldpath, oldmode, oldsha),
                                    (newpath, newmode, newsha),
                                    diff_binary=diff_binary)


def git_am_patch_split(f):
    """Parse a git-am-style patch and split it up into bits.

    :param f: File-like object to parse
    :return: Tuple with commit object, diff contents and git version
    """
    msg = rfc822.Message(f)
    c = Commit()
    c.author = msg["from"]
    c.committer = msg["from"]
    try:
        patch_tag_start = msg["subject"].index("[PATCH")
    except ValueError:
        subject = msg["subject"]
    else:
        close = msg["subject"].index("] ", patch_tag_start)
        subject = msg["subject"][close+2:]
    c.message = subject.replace("\n", "") + "\n"
    first = True
    for l in f:
        if l == "---\n":
            break
        if first:
            if l.startswith("From: "):
                c.author = l[len("From: "):].rstrip()
            else:
                c.message += "\n" + l
            first = False
        else:
            c.message += l
    diff = ""
    for l in f:
        if l == "-- \n":
            break
        diff += l
    try:
        version = f.next().rstrip("\n")
    except StopIteration:
        version = None
    return c, diff, version

########NEW FILE########
__FILENAME__ = protocol
# protocol.py -- Shared parts of the git protocols
# Copyright (C) 2008 John Carr <john.carr@unrouted.co.uk>
# Copyright (C) 2008 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Generic functions for talking the git smart server protocol."""

from cStringIO import StringIO
import socket

from dulwich.errors import (
    HangupException,
    GitProtocolError,
    )
from dulwich._compat import (
    SEEK_END,
    )

TCP_GIT_PORT = 9418

ZERO_SHA = "0" * 40

SINGLE_ACK = 0
MULTI_ACK = 1
MULTI_ACK_DETAILED = 2


class ProtocolFile(object):
    """A dummy file for network ops that expect file-like objects."""

    def __init__(self, read, write):
        self.read = read
        self.write = write

    def tell(self):
        pass

    def close(self):
        pass


def pkt_line(data):
    """Wrap data in a pkt-line.

    :param data: The data to wrap, as a str or None.
    :return: The data prefixed with its length in pkt-line format; if data was
        None, returns the flush-pkt ('0000').
    """
    if data is None:
        return '0000'
    return '%04x%s' % (len(data) + 4, data)


class Protocol(object):
    """Class for interacting with a remote git process over the wire.

    Parts of the git wire protocol use 'pkt-lines' to communicate. A pkt-line
    consists of the length of the line as a 4-byte hex string, followed by the
    payload data. The length includes the 4-byte header. The special line '0000'
    indicates the end of a section of input and is called a 'flush-pkt'.

    For details on the pkt-line format, see the cgit distribution:
        Documentation/technical/protocol-common.txt
    """

    def __init__(self, read, write, report_activity=None):
        self.read = read
        self.write = write
        self.report_activity = report_activity
        self._readahead = None

    def read_pkt_line(self):
        """Reads a pkt-line from the remote git process.

        This method may read from the readahead buffer; see unread_pkt_line.

        :return: The next string from the stream, without the length prefix, or
            None for a flush-pkt ('0000').
        """
        if self._readahead is None:
            read = self.read
        else:
            read = self._readahead.read
            self._readahead = None

        try:
            sizestr = read(4)
            if not sizestr:
                raise HangupException()
            size = int(sizestr, 16)
            if size == 0:
                if self.report_activity:
                    self.report_activity(4, 'read')
                return None
            if self.report_activity:
                self.report_activity(size, 'read')
            return read(size-4)
        except socket.error, e:
            raise GitProtocolError(e)

    def eof(self):
        """Test whether the protocol stream has reached EOF.

        Note that this refers to the actual stream EOF and not just a flush-pkt.

        :return: True if the stream is at EOF, False otherwise.
        """
        try:
            next_line = self.read_pkt_line()
        except HangupException:
            return True
        self.unread_pkt_line(next_line)
        return False

    def unread_pkt_line(self, data):
        """Unread a single line of data into the readahead buffer.

        This method can be used to unread a single pkt-line into a fixed
        readahead buffer.

        :param data: The data to unread, without the length prefix.
        :raise ValueError: If more than one pkt-line is unread.
        """
        if self._readahead is not None:
            raise ValueError('Attempted to unread multiple pkt-lines.')
        self._readahead = StringIO(pkt_line(data))

    def read_pkt_seq(self):
        """Read a sequence of pkt-lines from the remote git process.

        :return: Yields each line of data up to but not including the next flush-pkt.
        """
        pkt = self.read_pkt_line()
        while pkt:
            yield pkt
            pkt = self.read_pkt_line()

    def write_pkt_line(self, line):
        """Sends a pkt-line to the remote git process.

        :param line: A string containing the data to send, without the length
            prefix.
        """
        try:
            line = pkt_line(line)
            self.write(line)
            if self.report_activity:
                self.report_activity(len(line), 'write')
        except socket.error, e:
            raise GitProtocolError(e)

    def write_file(self):
        """Return a writable file-like object for this protocol."""

        class ProtocolFile(object):

            def __init__(self, proto):
                self._proto = proto
                self._offset = 0

            def write(self, data):
                self._proto.write(data)
                self._offset += len(data)

            def tell(self):
                return self._offset

            def close(self):
                pass

        return ProtocolFile(self)

    def write_sideband(self, channel, blob):
        """Write multiplexed data to the sideband.

        :param channel: An int specifying the channel to write to.
        :param blob: A blob of data (as a string) to send on this channel.
        """
        # a pktline can be a max of 65520. a sideband line can therefore be
        # 65520-5 = 65515
        # WTF: Why have the len in ASCII, but the channel in binary.
        while blob:
            self.write_pkt_line("%s%s" % (chr(channel), blob[:65515]))
            blob = blob[65515:]

    def send_cmd(self, cmd, *args):
        """Send a command and some arguments to a git server.

        Only used for the TCP git protocol (git://).

        :param cmd: The remote service to access.
        :param args: List of arguments to send to remove service.
        """
        self.write_pkt_line("%s %s" % (cmd, "".join(["%s\0" % a for a in args])))

    def read_cmd(self):
        """Read a command and some arguments from the git client

        Only used for the TCP git protocol (git://).

        :return: A tuple of (command, [list of arguments]).
        """
        line = self.read_pkt_line()
        splice_at = line.find(" ")
        cmd, args = line[:splice_at], line[splice_at+1:]
        assert args[-1] == "\x00"
        return cmd, args[:-1].split(chr(0))


_RBUFSIZE = 8192  # Default read buffer size.


class ReceivableProtocol(Protocol):
    """Variant of Protocol that allows reading up to a size without blocking.

    This class has a recv() method that behaves like socket.recv() in addition
    to a read() method.

    If you want to read n bytes from the wire and block until exactly n bytes
    (or EOF) are read, use read(n). If you want to read at most n bytes from the
    wire but don't care if you get less, use recv(n). Note that recv(n) will
    still block until at least one byte is read.
    """

    def __init__(self, recv, write, report_activity=None, rbufsize=_RBUFSIZE):
        super(ReceivableProtocol, self).__init__(self.read, write,
                                                 report_activity)
        self._recv = recv
        self._rbuf = StringIO()
        self._rbufsize = rbufsize

    def read(self, size):
        # From _fileobj.read in socket.py in the Python 2.6.5 standard library,
        # with the following modifications:
        #  - omit the size <= 0 branch
        #  - seek back to start rather than 0 in case some buffer has been
        #    consumed.
        #  - use SEEK_END instead of the magic number.
        # Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved
        # Licensed under the Python Software Foundation License.
        # TODO: see if buffer is more efficient than cStringIO.
        assert size > 0

        # Our use of StringIO rather than lists of string objects returned by
        # recv() minimizes memory usage and fragmentation that occurs when
        # rbufsize is large compared to the typical return value of recv().
        buf = self._rbuf
        start = buf.tell()
        buf.seek(0, SEEK_END)
        # buffer may have been partially consumed by recv()
        buf_len = buf.tell() - start
        if buf_len >= size:
            # Already have size bytes in our buffer?  Extract and return.
            buf.seek(start)
            rv = buf.read(size)
            self._rbuf = StringIO()
            self._rbuf.write(buf.read())
            self._rbuf.seek(0)
            return rv

        self._rbuf = StringIO()  # reset _rbuf.  we consume it via buf.
        while True:
            left = size - buf_len
            # recv() will malloc the amount of memory given as its
            # parameter even though it often returns much less data
            # than that.  The returned data string is short lived
            # as we copy it into a StringIO and free it.  This avoids
            # fragmentation issues on many platforms.
            data = self._recv(left)
            if not data:
                break
            n = len(data)
            if n == size and not buf_len:
                # Shortcut.  Avoid buffer data copies when:
                # - We have no data in our buffer.
                # AND
                # - Our call to recv returned exactly the
                #   number of bytes we were asked to read.
                return data
            if n == left:
                buf.write(data)
                del data  # explicit free
                break
            assert n <= left, "_recv(%d) returned %d bytes" % (left, n)
            buf.write(data)
            buf_len += n
            del data  # explicit free
            #assert buf_len == buf.tell()
        buf.seek(start)
        return buf.read()

    def recv(self, size):
        assert size > 0

        buf = self._rbuf
        start = buf.tell()
        buf.seek(0, SEEK_END)
        buf_len = buf.tell()
        buf.seek(start)

        left = buf_len - start
        if not left:
            # only read from the wire if our read buffer is exhausted
            data = self._recv(self._rbufsize)
            if len(data) == size:
                # shortcut: skip the buffer if we read exactly size bytes
                return data
            buf = StringIO()
            buf.write(data)
            buf.seek(0)
            del data  # explicit free
            self._rbuf = buf
        return buf.read(size)


def extract_capabilities(text):
    """Extract a capabilities list from a string, if present.

    :param text: String to extract from
    :return: Tuple with text with capabilities removed and list of capabilities
    """
    if not "\0" in text:
        return text, []
    text, capabilities = text.rstrip().split("\0")
    return (text, capabilities.strip().split(" "))


def extract_want_line_capabilities(text):
    """Extract a capabilities list from a want line, if present.

    Note that want lines have capabilities separated from the rest of the line
    by a space instead of a null byte. Thus want lines have the form:

        want obj-id cap1 cap2 ...

    :param text: Want line to extract from
    :return: Tuple with text with capabilities removed and list of capabilities
    """
    split_text = text.rstrip().split(" ")
    if len(split_text) < 3:
        return text, []
    return (" ".join(split_text[:2]), split_text[2:])


def ack_type(capabilities):
    """Extract the ack type from a capabilities list."""
    if 'multi_ack_detailed' in capabilities:
        return MULTI_ACK_DETAILED
    elif 'multi_ack' in capabilities:
        return MULTI_ACK
    return SINGLE_ACK


class BufferedPktLineWriter(object):
    """Writer that wraps its data in pkt-lines and has an independent buffer.

    Consecutive calls to write() wrap the data in a pkt-line and then buffers it
    until enough lines have been written such that their total length (including
    length prefix) reach the buffer size.
    """

    def __init__(self, write, bufsize=65515):
        """Initialize the BufferedPktLineWriter.

        :param write: A write callback for the underlying writer.
        :param bufsize: The internal buffer size, including length prefixes.
        """
        self._write = write
        self._bufsize = bufsize
        self._wbuf = StringIO()
        self._buflen = 0

    def write(self, data):
        """Write data, wrapping it in a pkt-line."""
        line = pkt_line(data)
        line_len = len(line)
        over = self._buflen + line_len - self._bufsize
        if over >= 0:
            start = line_len - over
            self._wbuf.write(line[:start])
            self.flush()
        else:
            start = 0
        saved = line[start:]
        self._wbuf.write(saved)
        self._buflen += len(saved)

    def flush(self):
        """Flush all data from the buffer."""
        data = self._wbuf.getvalue()
        if data:
            self._write(data)
        self._len = 0
        self._wbuf = StringIO()


class PktLineParser(object):
    """Packet line parser that hands completed packets off to a callback.
    """

    def __init__(self, handle_pkt):
        self.handle_pkt = handle_pkt
        self._readahead = StringIO()

    def parse(self, data):
        """Parse a fragment of data and call back for any completed packets.
        """
        self._readahead.write(data)
        buf = self._readahead.getvalue()
        if len(buf) < 4:
            return
        while len(buf) >= 4:
            size = int(buf[:4], 16)
            if size == 0:
                self.handle_pkt(None)
                buf = buf[4:]
            elif size <= len(buf):
                self.handle_pkt(buf[4:size])
                buf = buf[size:]
            else:
                break
        self._readahead = StringIO()
        self._readahead.write(buf)

    def get_tail(self):
        """Read back any unused data."""
        return self._readahead.getvalue()

########NEW FILE########
__FILENAME__ = repo
# repo.py -- For dealing with git repositories.
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.


"""Repository access.

This module contains the base class for git repositories
(BaseRepo) and an implementation which uses a repository on
local disk (Repo).

"""

from cStringIO import StringIO
import errno
import os

from dulwich.errors import (
    NoIndexPresent,
    NotBlobError,
    NotCommitError,
    NotGitRepository,
    NotTreeError,
    NotTagError,
    PackedRefsException,
    CommitError,
    RefFormatError,
    HookError,
    )
from dulwich.file import (
    ensure_dir_exists,
    GitFile,
    )
from dulwich.object_store import (
    DiskObjectStore,
    MemoryObjectStore,
    )
from dulwich.objects import (
    Blob,
    Commit,
    ShaFile,
    Tag,
    Tree,
    hex_to_sha,
    )

from dulwich.hooks import (
    PreCommitShellHook,
    PostCommitShellHook,
    CommitMsgShellHook,
)

import warnings


OBJECTDIR = 'objects'
SYMREF = 'ref: '
REFSDIR = 'refs'
REFSDIR_TAGS = 'tags'
REFSDIR_HEADS = 'heads'
INDEX_FILENAME = "index"

BASE_DIRECTORIES = [
    ["branches"],
    [REFSDIR],
    [REFSDIR, REFSDIR_TAGS],
    [REFSDIR, REFSDIR_HEADS],
    ["hooks"],
    ["info"]
    ]


def read_info_refs(f):
    ret = {}
    for l in f.readlines():
        (sha, name) = l.rstrip("\r\n").split("\t", 1)
        ret[name] = sha
    return ret


def check_ref_format(refname):
    """Check if a refname is correctly formatted.

    Implements all the same rules as git-check-ref-format[1].

    [1] http://www.kernel.org/pub/software/scm/git/docs/git-check-ref-format.html

    :param refname: The refname to check
    :return: True if refname is valid, False otherwise
    """
    # These could be combined into one big expression, but are listed separately
    # to parallel [1].
    if '/.' in refname or refname.startswith('.'):
        return False
    if '/' not in refname:
        return False
    if '..' in refname:
        return False
    for c in refname:
        if ord(c) < 040 or c in '\177 ~^:?*[':
            return False
    if refname[-1] in '/.':
        return False
    if refname.endswith('.lock'):
        return False
    if '@{' in refname:
        return False
    if '\\' in refname:
        return False
    return True


class RefsContainer(object):
    """A container for refs."""

    def set_ref(self, name, other):
        warnings.warn("RefsContainer.set_ref() is deprecated."
            "Use set_symblic_ref instead.",
            category=DeprecationWarning, stacklevel=2)
        return self.set_symbolic_ref(name, other)

    def set_symbolic_ref(self, name, other):
        """Make a ref point at another ref.

        :param name: Name of the ref to set
        :param other: Name of the ref to point at
        """
        raise NotImplementedError(self.set_symbolic_ref)

    def get_packed_refs(self):
        """Get contents of the packed-refs file.

        :return: Dictionary mapping ref names to SHA1s

        :note: Will return an empty dictionary when no packed-refs file is
            present.
        """
        raise NotImplementedError(self.get_packed_refs)

    def get_peeled(self, name):
        """Return the cached peeled value of a ref, if available.

        :param name: Name of the ref to peel
        :return: The peeled value of the ref. If the ref is known not point to a
            tag, this will be the SHA the ref refers to. If the ref may point to
            a tag, but no cached information is available, None is returned.
        """
        return None

    def import_refs(self, base, other):
        for name, value in other.iteritems():
            self["%s/%s" % (base, name)] = value

    def allkeys(self):
        """All refs present in this container."""
        raise NotImplementedError(self.allkeys)

    def keys(self, base=None):
        """Refs present in this container.

        :param base: An optional base to return refs under.
        :return: An unsorted set of valid refs in this container, including
            packed refs.
        """
        if base is not None:
            return self.subkeys(base)
        else:
            return self.allkeys()

    def subkeys(self, base):
        """Refs present in this container under a base.

        :param base: The base to return refs under.
        :return: A set of valid refs in this container under the base; the base
            prefix is stripped from the ref names returned.
        """
        keys = set()
        base_len = len(base) + 1
        for refname in self.allkeys():
            if refname.startswith(base):
                keys.add(refname[base_len:])
        return keys

    def as_dict(self, base=None):
        """Return the contents of this container as a dictionary.

        """
        ret = {}
        keys = self.keys(base)
        if base is None:
            base = ""
        for key in keys:
            try:
                ret[key] = self[("%s/%s" % (base, key)).strip("/")]
            except KeyError:
                continue  # Unable to resolve

        return ret

    def _check_refname(self, name):
        """Ensure a refname is valid and lives in refs or is HEAD.

        HEAD is not a valid refname according to git-check-ref-format, but this
        class needs to be able to touch HEAD. Also, check_ref_format expects
        refnames without the leading 'refs/', but this class requires that
        so it cannot touch anything outside the refs dir (or HEAD).

        :param name: The name of the reference.
        :raises KeyError: if a refname is not HEAD or is otherwise not valid.
        """
        if name in ('HEAD', 'refs/stash'):
            return
        if not name.startswith('refs/') or not check_ref_format(name[5:]):
            raise RefFormatError(name)

    def read_ref(self, refname):
        """Read a reference without following any references.

        :param refname: The name of the reference
        :return: The contents of the ref file, or None if it does
            not exist.
        """
        contents = self.read_loose_ref(refname)
        if not contents:
            contents = self.get_packed_refs().get(refname, None)
        return contents

    def read_loose_ref(self, name):
        """Read a loose reference and return its contents.

        :param name: the refname to read
        :return: The contents of the ref file, or None if it does
            not exist.
        """
        raise NotImplementedError(self.read_loose_ref)

    def _follow(self, name):
        """Follow a reference name.

        :return: a tuple of (refname, sha), where refname is the name of the
            last reference in the symbolic reference chain
        """
        contents = SYMREF + name
        depth = 0
        while contents.startswith(SYMREF):
            refname = contents[len(SYMREF):]
            contents = self.read_ref(refname)
            if not contents:
                break
            depth += 1
            if depth > 5:
                raise KeyError(name)
        return refname, contents

    def __contains__(self, refname):
        if self.read_ref(refname):
            return True
        return False

    def __getitem__(self, name):
        """Get the SHA1 for a reference name.

        This method follows all symbolic references.
        """
        _, sha = self._follow(name)
        if sha is None:
            raise KeyError(name)
        return sha

    def set_if_equals(self, name, old_ref, new_ref):
        """Set a refname to new_ref only if it currently equals old_ref.

        This method follows all symbolic references if applicable for the
        subclass, and can be used to perform an atomic compare-and-swap
        operation.

        :param name: The refname to set.
        :param old_ref: The old sha the refname must refer to, or None to set
            unconditionally.
        :param new_ref: The new sha the refname will refer to.
        :return: True if the set was successful, False otherwise.
        """
        raise NotImplementedError(self.set_if_equals)

    def add_if_new(self, name, ref):
        """Add a new reference only if it does not already exist."""
        raise NotImplementedError(self.add_if_new)

    def __setitem__(self, name, ref):
        """Set a reference name to point to the given SHA1.

        This method follows all symbolic references if applicable for the
        subclass.

        :note: This method unconditionally overwrites the contents of a
            reference. To update atomically only if the reference has not
            changed, use set_if_equals().
        :param name: The refname to set.
        :param ref: The new sha the refname will refer to.
        """
        self.set_if_equals(name, None, ref)

    def remove_if_equals(self, name, old_ref):
        """Remove a refname only if it currently equals old_ref.

        This method does not follow symbolic references, even if applicable for
        the subclass. It can be used to perform an atomic compare-and-delete
        operation.

        :param name: The refname to delete.
        :param old_ref: The old sha the refname must refer to, or None to delete
            unconditionally.
        :return: True if the delete was successful, False otherwise.
        """
        raise NotImplementedError(self.remove_if_equals)

    def __delitem__(self, name):
        """Remove a refname.

        This method does not follow symbolic references, even if applicable for
        the subclass.

        :note: This method unconditionally deletes the contents of a reference.
            To delete atomically only if the reference has not changed, use
            remove_if_equals().

        :param name: The refname to delete.
        """
        self.remove_if_equals(name, None)


class DictRefsContainer(RefsContainer):
    """RefsContainer backed by a simple dict.

    This container does not support symbolic or packed references and is not
    threadsafe.
    """

    def __init__(self, refs):
        self._refs = refs
        self._peeled = {}

    def allkeys(self):
        return self._refs.keys()

    def read_loose_ref(self, name):
        return self._refs.get(name, None)

    def get_packed_refs(self):
        return {}

    def set_symbolic_ref(self, name, other):
        self._refs[name] = SYMREF + other

    def set_if_equals(self, name, old_ref, new_ref):
        if old_ref is not None and self._refs.get(name, None) != old_ref:
            return False
        realname, _ = self._follow(name)
        self._check_refname(realname)
        self._refs[realname] = new_ref
        return True

    def add_if_new(self, name, ref):
        if name in self._refs:
            return False
        self._refs[name] = ref
        return True

    def remove_if_equals(self, name, old_ref):
        if old_ref is not None and self._refs.get(name, None) != old_ref:
            return False
        del self._refs[name]
        return True

    def get_peeled(self, name):
        return self._peeled.get(name)

    def _update(self, refs):
        """Update multiple refs; intended only for testing."""
        # TODO(dborowitz): replace this with a public function that uses
        # set_if_equal.
        self._refs.update(refs)

    def _update_peeled(self, peeled):
        """Update cached peeled refs; intended only for testing."""
        self._peeled.update(peeled)


class InfoRefsContainer(RefsContainer):
    """Refs container that reads refs from a info/refs file."""

    def __init__(self, f):
        self._refs = {}
        self._peeled = {}
        for l in f.readlines():
            sha, name = l.rstrip("\n").split("\t")
            if name.endswith("^{}"):
                name = name[:-3]
                if not check_ref_format(name):
                    raise ValueError("invalid ref name '%s'" % name)
                self._peeled[name] = sha
            else:
                if not check_ref_format(name):
                    raise ValueError("invalid ref name '%s'" % name)
                self._refs[name] = sha

    def allkeys(self):
        return self._refs.keys()

    def read_loose_ref(self, name):
        return self._refs.get(name, None)

    def get_packed_refs(self):
        return {}

    def get_peeled(self, name):
        try:
            return self._peeled[name]
        except KeyError:
            return self._refs[name]


class DiskRefsContainer(RefsContainer):
    """Refs container that reads refs from disk."""

    def __init__(self, path):
        self.path = path
        self._packed_refs = None
        self._peeled_refs = None

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.path)

    def subkeys(self, base):
        keys = set()
        path = self.refpath(base)
        for root, dirs, files in os.walk(path):
            dir = root[len(path):].strip(os.path.sep).replace(os.path.sep, "/")
            for filename in files:
                refname = ("%s/%s" % (dir, filename)).strip("/")
                # check_ref_format requires at least one /, so we prepend the
                # base before calling it.
                if check_ref_format("%s/%s" % (base, refname)):
                    keys.add(refname)
        for key in self.get_packed_refs():
            if key.startswith(base):
                keys.add(key[len(base):].strip("/"))
        return keys

    def allkeys(self):
        keys = set()
        if os.path.exists(self.refpath("HEAD")):
            keys.add("HEAD")
        path = self.refpath("")
        for root, dirs, files in os.walk(self.refpath("refs")):
            dir = root[len(path):].strip(os.path.sep).replace(os.path.sep, "/")
            for filename in files:
                refname = ("%s/%s" % (dir, filename)).strip("/")
                if check_ref_format(refname):
                    keys.add(refname)
        keys.update(self.get_packed_refs())
        return keys

    def refpath(self, name):
        """Return the disk path of a ref.

        """
        if os.path.sep != "/":
            name = name.replace("/", os.path.sep)
        return os.path.join(self.path, name)

    def get_packed_refs(self):
        """Get contents of the packed-refs file.

        :return: Dictionary mapping ref names to SHA1s

        :note: Will return an empty dictionary when no packed-refs file is
            present.
        """
        # TODO: invalidate the cache on repacking
        if self._packed_refs is None:
            # set both to empty because we want _peeled_refs to be
            # None if and only if _packed_refs is also None.
            self._packed_refs = {}
            self._peeled_refs = {}
            path = os.path.join(self.path, 'packed-refs')
            try:
                f = GitFile(path, 'rb')
            except IOError, e:
                if e.errno == errno.ENOENT:
                    return {}
                raise
            try:
                first_line = iter(f).next().rstrip()
                if (first_line.startswith("# pack-refs") and " peeled" in
                        first_line):
                    for sha, name, peeled in read_packed_refs_with_peeled(f):
                        self._packed_refs[name] = sha
                        if peeled:
                            self._peeled_refs[name] = peeled
                else:
                    f.seek(0)
                    for sha, name in read_packed_refs(f):
                        self._packed_refs[name] = sha
            finally:
                f.close()
        return self._packed_refs

    def get_peeled(self, name):
        """Return the cached peeled value of a ref, if available.

        :param name: Name of the ref to peel
        :return: The peeled value of the ref. If the ref is known not point to a
            tag, this will be the SHA the ref refers to. If the ref may point to
            a tag, but no cached information is available, None is returned.
        """
        self.get_packed_refs()
        if self._peeled_refs is None or name not in self._packed_refs:
            # No cache: no peeled refs were read, or this ref is loose
            return None
        if name in self._peeled_refs:
            return self._peeled_refs[name]
        else:
            # Known not peelable
            return self[name]

    def read_loose_ref(self, name):
        """Read a reference file and return its contents.

        If the reference file a symbolic reference, only read the first line of
        the file. Otherwise, only read the first 40 bytes.

        :param name: the refname to read, relative to refpath
        :return: The contents of the ref file, or None if the file does not
            exist.
        :raises IOError: if any other error occurs
        """
        filename = self.refpath(name)
        try:
            f = GitFile(filename, 'rb')
            try:
                header = f.read(len(SYMREF))
                if header == SYMREF:
                    # Read only the first line
                    return header + iter(f).next().rstrip("\r\n")
                else:
                    # Read only the first 40 bytes
                    return header + f.read(40 - len(SYMREF))
            finally:
                f.close()
        except IOError, e:
            if e.errno == errno.ENOENT:
                return None
            raise

    def _remove_packed_ref(self, name):
        if self._packed_refs is None:
            return
        filename = os.path.join(self.path, 'packed-refs')
        # reread cached refs from disk, while holding the lock
        f = GitFile(filename, 'wb')
        try:
            self._packed_refs = None
            self.get_packed_refs()

            if name not in self._packed_refs:
                return

            del self._packed_refs[name]
            if name in self._peeled_refs:
                del self._peeled_refs[name]
            write_packed_refs(f, self._packed_refs, self._peeled_refs)
            f.close()
        finally:
            f.abort()

    def set_symbolic_ref(self, name, other):
        """Make a ref point at another ref.

        :param name: Name of the ref to set
        :param other: Name of the ref to point at
        """
        self._check_refname(name)
        self._check_refname(other)
        filename = self.refpath(name)
        try:
            f = GitFile(filename, 'wb')
            try:
                f.write(SYMREF + other + '\n')
            except (IOError, OSError):
                f.abort()
                raise
        finally:
            f.close()

    def set_if_equals(self, name, old_ref, new_ref):
        """Set a refname to new_ref only if it currently equals old_ref.

        This method follows all symbolic references, and can be used to perform
        an atomic compare-and-swap operation.

        :param name: The refname to set.
        :param old_ref: The old sha the refname must refer to, or None to set
            unconditionally.
        :param new_ref: The new sha the refname will refer to.
        :return: True if the set was successful, False otherwise.
        """
        self._check_refname(name)
        try:
            realname, _ = self._follow(name)
        except KeyError:
            realname = name
        filename = self.refpath(realname)
        ensure_dir_exists(os.path.dirname(filename))
        f = GitFile(filename, 'wb')
        try:
            if old_ref is not None:
                try:
                    # read again while holding the lock
                    orig_ref = self.read_loose_ref(realname)
                    if orig_ref is None:
                        orig_ref = self.get_packed_refs().get(realname, None)
                    if orig_ref != old_ref:
                        f.abort()
                        return False
                except (OSError, IOError):
                    f.abort()
                    raise
            try:
                f.write(new_ref + "\n")
            except (OSError, IOError):
                f.abort()
                raise
        finally:
            f.close()
        return True

    def add_if_new(self, name, ref):
        """Add a new reference only if it does not already exist.

        This method follows symrefs, and only ensures that the last ref in the
        chain does not exist.

        :param name: The refname to set.
        :param ref: The new sha the refname will refer to.
        :return: True if the add was successful, False otherwise.
        """
        try:
            realname, contents = self._follow(name)
            if contents is not None:
                return False
        except KeyError:
            realname = name
        self._check_refname(realname)
        filename = self.refpath(realname)
        ensure_dir_exists(os.path.dirname(filename))
        f = GitFile(filename, 'wb')
        try:
            if os.path.exists(filename) or name in self.get_packed_refs():
                f.abort()
                return False
            try:
                f.write(ref + "\n")
            except (OSError, IOError):
                f.abort()
                raise
        finally:
            f.close()
        return True

    def remove_if_equals(self, name, old_ref):
        """Remove a refname only if it currently equals old_ref.

        This method does not follow symbolic references. It can be used to
        perform an atomic compare-and-delete operation.

        :param name: The refname to delete.
        :param old_ref: The old sha the refname must refer to, or None to delete
            unconditionally.
        :return: True if the delete was successful, False otherwise.
        """
        self._check_refname(name)
        filename = self.refpath(name)
        ensure_dir_exists(os.path.dirname(filename))
        f = GitFile(filename, 'wb')
        try:
            if old_ref is not None:
                orig_ref = self.read_loose_ref(name)
                if orig_ref is None:
                    orig_ref = self.get_packed_refs().get(name, None)
                if orig_ref != old_ref:
                    return False
            # may only be packed
            try:
                os.remove(filename)
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise
            self._remove_packed_ref(name)
        finally:
            # never write, we just wanted the lock
            f.abort()
        return True


def _split_ref_line(line):
    """Split a single ref line into a tuple of SHA1 and name."""
    fields = line.rstrip("\n").split(" ")
    if len(fields) != 2:
        raise PackedRefsException("invalid ref line '%s'" % line)
    sha, name = fields
    try:
        hex_to_sha(sha)
    except (AssertionError, TypeError), e:
        raise PackedRefsException(e)
    if not check_ref_format(name):
        raise PackedRefsException("invalid ref name '%s'" % name)
    return (sha, name)


def read_packed_refs(f):
    """Read a packed refs file.

    :param f: file-like object to read from
    :return: Iterator over tuples with SHA1s and ref names.
    """
    for l in f:
        if l[0] == "#":
            # Comment
            continue
        if l[0] == "^":
            raise PackedRefsException(
              "found peeled ref in packed-refs without peeled")
        yield _split_ref_line(l)


def read_packed_refs_with_peeled(f):
    """Read a packed refs file including peeled refs.

    Assumes the "# pack-refs with: peeled" line was already read. Yields tuples
    with ref names, SHA1s, and peeled SHA1s (or None).

    :param f: file-like object to read from, seek'ed to the second line
    """
    last = None
    for l in f:
        if l[0] == "#":
            continue
        l = l.rstrip("\r\n")
        if l[0] == "^":
            if not last:
                raise PackedRefsException("unexpected peeled ref line")
            try:
                hex_to_sha(l[1:])
            except (AssertionError, TypeError), e:
                raise PackedRefsException(e)
            sha, name = _split_ref_line(last)
            last = None
            yield (sha, name, l[1:])
        else:
            if last:
                sha, name = _split_ref_line(last)
                yield (sha, name, None)
            last = l
    if last:
        sha, name = _split_ref_line(last)
        yield (sha, name, None)


def write_packed_refs(f, packed_refs, peeled_refs=None):
    """Write a packed refs file.

    :param f: empty file-like object to write to
    :param packed_refs: dict of refname to sha of packed refs to write
    :param peeled_refs: dict of refname to peeled value of sha
    """
    if peeled_refs is None:
        peeled_refs = {}
    else:
        f.write('# pack-refs with: peeled\n')
    for refname in sorted(packed_refs.iterkeys()):
        f.write('%s %s\n' % (packed_refs[refname], refname))
        if refname in peeled_refs:
            f.write('^%s\n' % peeled_refs[refname])


class BaseRepo(object):
    """Base class for a git repository.

    :ivar object_store: Dictionary-like object for accessing
        the objects
    :ivar refs: Dictionary-like object with the refs in this
        repository
    """

    def __init__(self, object_store, refs):
        """Open a repository.

        This shouldn't be called directly, but rather through one of the
        base classes, such as MemoryRepo or Repo.

        :param object_store: Object store to use
        :param refs: Refs container to use
        """
        self.object_store = object_store
        self.refs = refs

        self.hooks = {}

    def _init_files(self, bare):
        """Initialize a default set of named files."""
        from dulwich.config import ConfigFile
        self._put_named_file('description', "Unnamed repository")
        f = StringIO()
        cf = ConfigFile()
        cf.set("core", "repositoryformatversion", "0")
        cf.set("core", "filemode", "true")
        cf.set("core", "bare", str(bare).lower())
        cf.set("core", "logallrefupdates", "true")
        cf.write_to_file(f)
        self._put_named_file('config', f.getvalue())
        self._put_named_file(os.path.join('info', 'exclude'), '')

    def get_named_file(self, path):
        """Get a file from the control dir with a specific name.

        Although the filename should be interpreted as a filename relative to
        the control dir in a disk-based Repo, the object returned need not be
        pointing to a file in that location.

        :param path: The path to the file, relative to the control dir.
        :return: An open file object, or None if the file does not exist.
        """
        raise NotImplementedError(self.get_named_file)

    def _put_named_file(self, path, contents):
        """Write a file to the control dir with the given name and contents.

        :param path: The path to the file, relative to the control dir.
        :param contents: A string to write to the file.
        """
        raise NotImplementedError(self._put_named_file)

    def open_index(self):
        """Open the index for this repository.

        :raise NoIndexPresent: If no index is present
        :return: The matching `Index`
        """
        raise NotImplementedError(self.open_index)

    def fetch(self, target, determine_wants=None, progress=None):
        """Fetch objects into another repository.

        :param target: The target repository
        :param determine_wants: Optional function to determine what refs to
            fetch.
        :param progress: Optional progress function
        """
        if determine_wants is None:
            determine_wants = lambda heads: heads.values()
        target.object_store.add_objects(
          self.fetch_objects(determine_wants, target.get_graph_walker(),
                             progress))
        return self.get_refs()

    def fetch_objects(self, determine_wants, graph_walker, progress,
                      get_tagged=None):
        """Fetch the missing objects required for a set of revisions.

        :param determine_wants: Function that takes a dictionary with heads
            and returns the list of heads to fetch.
        :param graph_walker: Object that can iterate over the list of revisions
            to fetch and has an "ack" method that will be called to acknowledge
            that a revision is present.
        :param progress: Simple progress function that will be called with
            updated progress strings.
        :param get_tagged: Function that returns a dict of pointed-to sha -> tag
            sha for including tags.
        :return: iterator over objects, with __len__ implemented
        """
        wants = determine_wants(self.get_refs())
        if type(wants) is not list:
            raise TypeError("determine_wants() did not return a list")
        if wants == []:
            # TODO(dborowitz): find a way to short-circuit that doesn't change
            # this interface.
            return []
        haves = self.object_store.find_common_revisions(graph_walker)
        return self.object_store.iter_shas(
          self.object_store.find_missing_objects(haves, wants, progress,
                                                 get_tagged))

    def get_graph_walker(self, heads=None):
        """Retrieve a graph walker.

        A graph walker is used by a remote repository (or proxy)
        to find out which objects are present in this repository.

        :param heads: Repository heads to use (optional)
        :return: A graph walker object
        """
        if heads is None:
            heads = self.refs.as_dict('refs/heads').values()
        return self.object_store.get_graph_walker(heads)

    def ref(self, name):
        """Return the SHA1 a ref is pointing to.

        :param name: Name of the ref to look up
        :raise KeyError: when the ref (or the one it points to) does not exist
        :return: SHA1 it is pointing at
        """
        return self.refs[name]

    def get_refs(self):
        """Get dictionary with all refs.

        :return: A ``dict`` mapping ref names to SHA1s
        """
        return self.refs.as_dict()

    def head(self):
        """Return the SHA1 pointed at by HEAD."""
        return self.refs['HEAD']

    def _get_object(self, sha, cls):
        assert len(sha) in (20, 40)
        ret = self.get_object(sha)
        if not isinstance(ret, cls):
            if cls is Commit:
                raise NotCommitError(ret)
            elif cls is Blob:
                raise NotBlobError(ret)
            elif cls is Tree:
                raise NotTreeError(ret)
            elif cls is Tag:
                raise NotTagError(ret)
            else:
                raise Exception("Type invalid: %r != %r" % (
                  ret.type_name, cls.type_name))
        return ret

    def get_object(self, sha):
        """Retrieve the object with the specified SHA.

        :param sha: SHA to retrieve
        :return: A ShaFile object
        :raise KeyError: when the object can not be found
        """
        return self.object_store[sha]

    def get_parents(self, sha):
        """Retrieve the parents of a specific commit.

        :param sha: SHA of the commit for which to retrieve the parents
        :return: List of parents
        """
        return self.commit(sha).parents

    def get_config(self):
        """Retrieve the config object.

        :return: `ConfigFile` object for the ``.git/config`` file.
        """
        raise NotImplementedError(self.get_config)

    def get_description(self):
        """Retrieve the description for this repository.

        :return: String with the description of the repository
            as set by the user.
        """
        raise NotImplementedError(self.get_description)

    def get_config_stack(self):
        """Return a config stack for this repository.

        This stack accesses the configuration for both this repository
        itself (.git/config) and the global configuration, which usually
        lives in ~/.gitconfig.

        :return: `Config` instance for this repository
        """
        from dulwich.config import StackedConfig
        backends = [self.get_config()] + StackedConfig.default_backends()
        return StackedConfig(backends, writable=backends[0])

    def commit(self, sha):
        """Retrieve the commit with a particular SHA.

        :param sha: SHA of the commit to retrieve
        :raise NotCommitError: If the SHA provided doesn't point at a Commit
        :raise KeyError: If the SHA provided didn't exist
        :return: A `Commit` object
        """
        warnings.warn("Repo.commit(sha) is deprecated. Use Repo[sha] instead.",
            category=DeprecationWarning, stacklevel=2)
        return self._get_object(sha, Commit)

    def tree(self, sha):
        """Retrieve the tree with a particular SHA.

        :param sha: SHA of the tree to retrieve
        :raise NotTreeError: If the SHA provided doesn't point at a Tree
        :raise KeyError: If the SHA provided didn't exist
        :return: A `Tree` object
        """
        warnings.warn("Repo.tree(sha) is deprecated. Use Repo[sha] instead.",
            category=DeprecationWarning, stacklevel=2)
        return self._get_object(sha, Tree)

    def tag(self, sha):
        """Retrieve the tag with a particular SHA.

        :param sha: SHA of the tag to retrieve
        :raise NotTagError: If the SHA provided doesn't point at a Tag
        :raise KeyError: If the SHA provided didn't exist
        :return: A `Tag` object
        """
        warnings.warn("Repo.tag(sha) is deprecated. Use Repo[sha] instead.",
            category=DeprecationWarning, stacklevel=2)
        return self._get_object(sha, Tag)

    def get_blob(self, sha):
        """Retrieve the blob with a particular SHA.

        :param sha: SHA of the blob to retrieve
        :raise NotBlobError: If the SHA provided doesn't point at a Blob
        :raise KeyError: If the SHA provided didn't exist
        :return: A `Blob` object
        """
        warnings.warn("Repo.get_blob(sha) is deprecated. Use Repo[sha] "
            "instead.", category=DeprecationWarning, stacklevel=2)
        return self._get_object(sha, Blob)

    def get_peeled(self, ref):
        """Get the peeled value of a ref.

        :param ref: The refname to peel.
        :return: The fully-peeled SHA1 of a tag object, after peeling all
            intermediate tags; if the original ref does not point to a tag, this
            will equal the original SHA1.
        """
        cached = self.refs.get_peeled(ref)
        if cached is not None:
            return cached
        return self.object_store.peel_sha(self.refs[ref]).id

    def get_walker(self, include=None, *args, **kwargs):
        """Obtain a walker for this repository.

        :param include: Iterable of SHAs of commits to include along with their
            ancestors. Defaults to [HEAD]
        :param exclude: Iterable of SHAs of commits to exclude along with their
            ancestors, overriding includes.
        :param order: ORDER_* constant specifying the order of results. Anything
            other than ORDER_DATE may result in O(n) memory usage.
        :param reverse: If True, reverse the order of output, requiring O(n)
            memory.
        :param max_entries: The maximum number of entries to yield, or None for
            no limit.
        :param paths: Iterable of file or subtree paths to show entries for.
        :param rename_detector: diff.RenameDetector object for detecting
            renames.
        :param follow: If True, follow path across renames/copies. Forces a
            default rename_detector.
        :param since: Timestamp to list commits after.
        :param until: Timestamp to list commits before.
        :param queue_cls: A class to use for a queue of commits, supporting the
            iterator protocol. The constructor takes a single argument, the
            Walker.
        :return: A `Walker` object
        """
        from dulwich.walk import Walker
        if include is None:
            include = [self.head()]
        if isinstance(include, str):
            include = [include]
        return Walker(self.object_store, include, *args, **kwargs)

    def revision_history(self, head):
        """Returns a list of the commits reachable from head.

        :param head: The SHA of the head to list revision history for.
        :return: A list of commit objects reachable from head, starting with
            head itself, in descending commit time order.
        :raise MissingCommitError: if any missing commits are referenced,
            including if the head parameter isn't the SHA of a commit.
        """
        warnings.warn("Repo.revision_history() is deprecated."
            "Use dulwich.walker.Walker(repo) instead.",
            category=DeprecationWarning, stacklevel=2)
        return [e.commit for e in self.get_walker(include=[head])]

    def __getitem__(self, name):
        """Retrieve a Git object by SHA1 or ref.

        :param name: A Git object SHA1 or a ref name
        :return: A `ShaFile` object, such as a Commit or Blob
        :raise KeyError: when the specified ref or object does not exist
        """
        if len(name) in (20, 40):
            try:
                return self.object_store[name]
            except (KeyError, ValueError):
                pass
        try:
            return self.object_store[self.refs[name]]
        except RefFormatError:
            raise KeyError(name)

    def __contains__(self, name):
        """Check if a specific Git object or ref is present.

        :param name: Git object SHA1 or ref name
        """
        if len(name) in (20, 40):
            return name in self.object_store or name in self.refs
        else:
            return name in self.refs

    def __setitem__(self, name, value):
        """Set a ref.

        :param name: ref name
        :param value: Ref value - either a ShaFile object, or a hex sha
        """
        if name.startswith("refs/") or name == "HEAD":
            if isinstance(value, ShaFile):
                self.refs[name] = value.id
            elif isinstance(value, str):
                self.refs[name] = value
            else:
                raise TypeError(value)
        else:
            raise ValueError(name)

    def __delitem__(self, name):
        """Remove a ref.

        :param name: Name of the ref to remove
        """
        if name.startswith("refs/") or name == "HEAD":
            del self.refs[name]
        else:
            raise ValueError(name)

    def _get_user_identity(self):
        """Determine the identity to use for new commits.
        """
        config = self.get_config_stack()
        return "%s <%s>" % (
            config.get(("user", ), "name"),
            config.get(("user", ), "email"))

    def do_commit(self, message=None, committer=None,
                  author=None, commit_timestamp=None,
                  commit_timezone=None, author_timestamp=None,
                  author_timezone=None, tree=None, encoding=None,
                  ref='HEAD', merge_heads=None):
        """Create a new commit.

        :param message: Commit message
        :param committer: Committer fullname
        :param author: Author fullname (defaults to committer)
        :param commit_timestamp: Commit timestamp (defaults to now)
        :param commit_timezone: Commit timestamp timezone (defaults to GMT)
        :param author_timestamp: Author timestamp (defaults to commit timestamp)
        :param author_timezone: Author timestamp timezone
            (defaults to commit timestamp timezone)
        :param tree: SHA1 of the tree root to use (if not specified the
            current index will be committed).
        :param encoding: Encoding
        :param ref: Optional ref to commit to (defaults to current branch)
        :param merge_heads: Merge heads (defaults to .git/MERGE_HEADS)
        :return: New commit SHA1
        """
        import time
        c = Commit()
        if tree is None:
            index = self.open_index()
            c.tree = index.commit(self.object_store)
        else:
            if len(tree) != 40:
                raise ValueError("tree must be a 40-byte hex sha string")
            c.tree = tree

        try:
            self.hooks['pre-commit'].execute()
        except HookError, e:
            raise CommitError(e)
        except KeyError:  # no hook defined, silent fallthrough
            pass

        if merge_heads is None:
            # FIXME: Read merge heads from .git/MERGE_HEADS
            merge_heads = []
        if committer is None:
            committer = self._get_user_identity()
        c.committer = committer
        if commit_timestamp is None:
            commit_timestamp = time.time()
        c.commit_time = int(commit_timestamp)
        if commit_timezone is None:
            # FIXME: Use current user timezone rather than UTC
            commit_timezone = 0
        c.commit_timezone = commit_timezone
        if author is None:
            author = committer
        c.author = author
        if author_timestamp is None:
            author_timestamp = commit_timestamp
        c.author_time = int(author_timestamp)
        if author_timezone is None:
            author_timezone = commit_timezone
        c.author_timezone = author_timezone
        if encoding is not None:
            c.encoding = encoding
        if message is None:
            # FIXME: Try to read commit message from .git/MERGE_MSG
            raise ValueError("No commit message specified")

        try:
            c.message = self.hooks['commit-msg'].execute(message)
            if c.message is None:
                c.message = message
        except HookError, e:
            raise CommitError(e)
        except KeyError:  # no hook defined, message not modified
            c.message = message

        try:
            old_head = self.refs[ref]
            c.parents = [old_head] + merge_heads
            self.object_store.add_object(c)
            ok = self.refs.set_if_equals(ref, old_head, c.id)
        except KeyError:
            c.parents = merge_heads
            self.object_store.add_object(c)
            ok = self.refs.add_if_new(ref, c.id)
        if not ok:
            # Fail if the atomic compare-and-swap failed, leaving the commit and
            # all its objects as garbage.
            raise CommitError("%s changed during commit" % (ref,))

        try:
            self.hooks['post-commit'].execute()
        except HookError, e:  # silent failure
            warnings.warn("post-commit hook failed: %s" % e, UserWarning)
        except KeyError:  # no hook defined, silent fallthrough
            pass

        return c.id


class Repo(BaseRepo):
    """A git repository backed by local disk.

    To open an existing repository, call the contructor with
    the path of the repository.

    To create a new repository, use the Repo.init class method.
    """

    def __init__(self, root):
        if os.path.isdir(os.path.join(root, ".git", OBJECTDIR)):
            self.bare = False
            self._controldir = os.path.join(root, ".git")
        elif (os.path.isdir(os.path.join(root, OBJECTDIR)) and
              os.path.isdir(os.path.join(root, REFSDIR))):
            self.bare = True
            self._controldir = root
        elif (os.path.isfile(os.path.join(root, ".git"))):
            import re
            f = open(os.path.join(root, ".git"), 'r')
            try:
                _, path = re.match('(gitdir: )(.+$)', f.read()).groups()
            finally:
                f.close()
            self.bare = False
            self._controldir = os.path.join(root, path)
        else:
            raise NotGitRepository(
                "No git repository was found at %(path)s" % dict(path=root)
            )
        self.path = root
        object_store = DiskObjectStore(os.path.join(self.controldir(),
                                                    OBJECTDIR))
        refs = DiskRefsContainer(self.controldir())
        BaseRepo.__init__(self, object_store, refs)

        self.hooks['pre-commit'] = PreCommitShellHook(self.controldir())
        self.hooks['commit-msg'] = CommitMsgShellHook(self.controldir())
        self.hooks['post-commit'] = PostCommitShellHook(self.controldir())

    def controldir(self):
        """Return the path of the control directory."""
        return self._controldir

    def _put_named_file(self, path, contents):
        """Write a file to the control dir with the given name and contents.

        :param path: The path to the file, relative to the control dir.
        :param contents: A string to write to the file.
        """
        path = path.lstrip(os.path.sep)
        f = GitFile(os.path.join(self.controldir(), path), 'wb')
        try:
            f.write(contents)
        finally:
            f.close()

    def get_named_file(self, path):
        """Get a file from the control dir with a specific name.

        Although the filename should be interpreted as a filename relative to
        the control dir in a disk-based Repo, the object returned need not be
        pointing to a file in that location.

        :param path: The path to the file, relative to the control dir.
        :return: An open file object, or None if the file does not exist.
        """
        # TODO(dborowitz): sanitize filenames, since this is used directly by
        # the dumb web serving code.
        path = path.lstrip(os.path.sep)
        try:
            return open(os.path.join(self.controldir(), path), 'rb')
        except (IOError, OSError), e:
            if e.errno == errno.ENOENT:
                return None
            raise

    def index_path(self):
        """Return path to the index file."""
        return os.path.join(self.controldir(), INDEX_FILENAME)

    def open_index(self):
        """Open the index for this repository.

        :raise NoIndexPresent: If no index is present
        :return: The matching `Index`
        """
        from dulwich.index import Index
        if not self.has_index():
            raise NoIndexPresent()
        return Index(self.index_path())

    def has_index(self):
        """Check if an index is present."""
        # Bare repos must never have index files; non-bare repos may have a
        # missing index file, which is treated as empty.
        return not self.bare

    def stage(self, paths):
        """Stage a set of paths.

        :param paths: List of paths, relative to the repository path
        """
        if isinstance(paths, basestring):
            paths = [paths]
        from dulwich.index import index_entry_from_stat
        index = self.open_index()
        for path in paths:
            full_path = os.path.join(self.path, path)
            try:
                st = os.stat(full_path)
            except OSError:
                # File no longer exists
                try:
                    del index[path]
                except KeyError:
                    pass  # already removed
            else:
                blob = Blob()
                f = open(full_path, 'rb')
                try:
                    blob.data = f.read()
                finally:
                    f.close()
                self.object_store.add_object(blob)
                index[path] = index_entry_from_stat(st, blob.id, 0)
        index.write()

    def clone(self, target_path, mkdir=True, bare=False,
            origin="origin"):
        """Clone this repository.

        :param target_path: Target path
        :param mkdir: Create the target directory
        :param bare: Whether to create a bare repository
        :param origin: Base name for refs in target repository
            cloned from this repository
        :return: Created repository as `Repo`
        """
        if not bare:
            target = self.init(target_path, mkdir=mkdir)
        else:
            target = self.init_bare(target_path)
        self.fetch(target)
        target.refs.import_refs(
            'refs/remotes/' + origin, self.refs.as_dict('refs/heads'))
        target.refs.import_refs(
            'refs/tags', self.refs.as_dict('refs/tags'))
        try:
            target.refs.add_if_new(
                'refs/heads/master',
                self.refs['refs/heads/master'])
        except KeyError:
            pass

        # Update target head
        head, head_sha = self.refs._follow('HEAD')
        if head is not None and head_sha is not None:
            target.refs.set_symbolic_ref('HEAD', head)
            target['HEAD'] = head_sha

            if not bare:
                # Checkout HEAD to target dir
                target._build_tree()

        return target

    def _build_tree(self):
        from dulwich.index import build_index_from_tree
        config = self.get_config()
        honor_filemode = config.get_boolean('core', 'filemode', os.name != "nt")
        return build_index_from_tree(self.path, self.index_path(),
                self.object_store, self['HEAD'].tree,
                honor_filemode=honor_filemode)

    def get_config(self):
        """Retrieve the config object.

        :return: `ConfigFile` object for the ``.git/config`` file.
        """
        from dulwich.config import ConfigFile
        path = os.path.join(self._controldir, 'config')
        try:
            return ConfigFile.from_path(path)
        except (IOError, OSError), e:
            if e.errno != errno.ENOENT:
                raise
            ret = ConfigFile()
            ret.path = path
            return ret

    def get_description(self):
        """Retrieve the description of this repository.

        :return: A string describing the repository or None.
        """
        path = os.path.join(self._controldir, 'description')
        try:
            f = GitFile(path, 'rb')
            try:
                return f.read()
            finally:
                f.close()
        except (IOError, OSError), e:
            if e.errno != errno.ENOENT:
                raise
            return None

    def __repr__(self):
        return "<Repo at %r>" % self.path

    @classmethod
    def _init_maybe_bare(cls, path, bare):
        for d in BASE_DIRECTORIES:
            os.mkdir(os.path.join(path, *d))
        DiskObjectStore.init(os.path.join(path, OBJECTDIR))
        ret = cls(path)
        ret.refs.set_symbolic_ref("HEAD", "refs/heads/master")
        ret._init_files(bare)
        return ret

    @classmethod
    def init(cls, path, mkdir=False):
        """Create a new repository.

        :param path: Path in which to create the repository
        :param mkdir: Whether to create the directory
        :return: `Repo` instance
        """
        if mkdir:
            os.mkdir(path)
        controldir = os.path.join(path, ".git")
        os.mkdir(controldir)
        cls._init_maybe_bare(controldir, False)
        return cls(path)

    @classmethod
    def init_bare(cls, path):
        """Create a new bare repository.

        ``path`` should already exist and be an emty directory.

        :param path: Path to create bare repository in
        :return: a `Repo` instance
        """
        return cls._init_maybe_bare(path, True)

    create = init_bare


class MemoryRepo(BaseRepo):
    """Repo that stores refs, objects, and named files in memory.

    MemoryRepos are always bare: they have no working tree and no index, since
    those have a stronger dependency on the filesystem.
    """

    def __init__(self):
        BaseRepo.__init__(self, MemoryObjectStore(), DictRefsContainer({}))
        self._named_files = {}
        self.bare = True

    def _put_named_file(self, path, contents):
        """Write a file to the control dir with the given name and contents.

        :param path: The path to the file, relative to the control dir.
        :param contents: A string to write to the file.
        """
        self._named_files[path] = contents

    def get_named_file(self, path):
        """Get a file from the control dir with a specific name.

        Although the filename should be interpreted as a filename relative to
        the control dir in a disk-baked Repo, the object returned need not be
        pointing to a file in that location.

        :param path: The path to the file, relative to the control dir.
        :return: An open file object, or None if the file does not exist.
        """
        contents = self._named_files.get(path, None)
        if contents is None:
            return None
        return StringIO(contents)

    def open_index(self):
        """Fail to open index for this repo, since it is bare.

        :raise NoIndexPresent: Raised when no index is present
        """
        raise NoIndexPresent()

    def get_config(self):
        """Retrieve the config object.

        :return: `ConfigFile` object.
        """
        from dulwich.config import ConfigFile
        return ConfigFile()

    def get_description(self):
        """Retrieve the repository description.

        This defaults to None, for no description.
        """
        return None

    @classmethod
    def init_bare(cls, objects, refs):
        """Create a new bare repository in memory.

        :param objects: Objects for the new repository,
            as iterable
        :param refs: Refs as dictionary, mapping names
            to object SHA1s
        """
        ret = cls()
        for obj in objects:
            ret.object_store.add_object(obj)
        for refname, sha in refs.iteritems():
            ret.refs[refname] = sha
        ret._init_files(bare=True)
        return ret

########NEW FILE########
__FILENAME__ = server
# server.py -- Implementation of the server side git protocols
# Copyright (C) 2008 John Carr <john.carr@unrouted.co.uk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Git smart network protocol server implementation.

For more detailed implementation on the network protocol, see the
Documentation/technical directory in the cgit distribution, and in particular:

* Documentation/technical/protocol-capabilities.txt
* Documentation/technical/pack-protocol.txt

Currently supported capabilities:

 * include-tag
 * thin-pack
 * multi_ack_detailed
 * multi_ack
 * side-band-64k
 * ofs-delta
 * no-progress
 * report-status
 * delete-refs

Known capabilities that are not supported:
 * shallow (http://pad.lv/909524)
"""

import collections
import os
import socket
import SocketServer
import sys
import zlib

from dulwich.errors import (
    ApplyDeltaError,
    ChecksumMismatch,
    GitProtocolError,
    NotGitRepository,
    UnexpectedCommandError,
    ObjectFormatException,
    )
from dulwich import log_utils
from dulwich.objects import (
    hex_to_sha,
    )
from dulwich.pack import (
    write_pack_objects,
    )
from dulwich.protocol import (
    BufferedPktLineWriter,
    MULTI_ACK,
    MULTI_ACK_DETAILED,
    Protocol,
    ProtocolFile,
    ReceivableProtocol,
    SINGLE_ACK,
    TCP_GIT_PORT,
    ZERO_SHA,
    ack_type,
    extract_capabilities,
    extract_want_line_capabilities,
    )
from dulwich.repo import (
    Repo,
    )


logger = log_utils.getLogger(__name__)


class Backend(object):
    """A backend for the Git smart server implementation."""

    def open_repository(self, path):
        """Open the repository at a path.

        :param path: Path to the repository
        :raise NotGitRepository: no git repository was found at path
        :return: Instance of BackendRepo
        """
        raise NotImplementedError(self.open_repository)


class BackendRepo(object):
    """Repository abstraction used by the Git server.

    Please note that the methods required here are a
    subset of those provided by dulwich.repo.Repo.
    """

    object_store = None
    refs = None

    def get_refs(self):
        """
        Get all the refs in the repository

        :return: dict of name -> sha
        """
        raise NotImplementedError

    def get_peeled(self, name):
        """Return the cached peeled value of a ref, if available.

        :param name: Name of the ref to peel
        :return: The peeled value of the ref. If the ref is known not point to
            a tag, this will be the SHA the ref refers to. If no cached
            information about a tag is available, this method may return None,
            but it should attempt to peel the tag if possible.
        """
        return None

    def fetch_objects(self, determine_wants, graph_walker, progress,
                      get_tagged=None):
        """
        Yield the objects required for a list of commits.

        :param progress: is a callback to send progress messages to the client
        :param get_tagged: Function that returns a dict of pointed-to sha -> tag
            sha for including tags.
        """
        raise NotImplementedError


class DictBackend(Backend):
    """Trivial backend that looks up Git repositories in a dictionary."""

    def __init__(self, repos):
        self.repos = repos

    def open_repository(self, path):
        logger.debug('Opening repository at %s', path)
        try:
            return self.repos[path]
        except KeyError:
            raise NotGitRepository(
                "No git repository was found at %(path)s" % dict(path=path)
            )


class FileSystemBackend(Backend):
    """Simple backend that looks up Git repositories in the local file system."""

    def open_repository(self, path):
        logger.debug('opening repository at %s', path)
        return Repo(path)


class Handler(object):
    """Smart protocol command handler base class."""

    def __init__(self, backend, proto, http_req=None):
        self.backend = backend
        self.proto = proto
        self.http_req = http_req
        self._client_capabilities = None

    @classmethod
    def capability_line(cls):
        return " ".join(cls.capabilities())

    @classmethod
    def capabilities(cls):
        raise NotImplementedError(cls.capabilities)

    @classmethod
    def innocuous_capabilities(cls):
        return ("include-tag", "thin-pack", "no-progress", "ofs-delta")

    @classmethod
    def required_capabilities(cls):
        """Return a list of capabilities that we require the client to have."""
        return []

    def set_client_capabilities(self, caps):
        allowable_caps = set(self.innocuous_capabilities())
        allowable_caps.update(self.capabilities())
        for cap in caps:
            if cap not in allowable_caps:
                raise GitProtocolError('Client asked for capability %s that '
                                       'was not advertised.' % cap)
        for cap in self.required_capabilities():
            if cap not in caps:
                raise GitProtocolError('Client does not support required '
                                       'capability %s.' % cap)
        self._client_capabilities = set(caps)
        logger.info('Client capabilities: %s', caps)

    def has_capability(self, cap):
        if self._client_capabilities is None:
            raise GitProtocolError('Server attempted to access capability %s '
                                   'before asking client' % cap)
        return cap in self._client_capabilities


class UploadPackHandler(Handler):
    """Protocol handler for uploading a pack to the server."""

    def __init__(self, backend, args, proto, http_req=None,
                 advertise_refs=False):
        Handler.__init__(self, backend, proto, http_req=http_req)
        self.repo = backend.open_repository(args[0])
        self._graph_walker = None
        self.advertise_refs = advertise_refs

    @classmethod
    def capabilities(cls):
        return ("multi_ack_detailed", "multi_ack", "side-band-64k", "thin-pack",
                "ofs-delta", "no-progress", "include-tag")

    @classmethod
    def required_capabilities(cls):
        return ("side-band-64k", "thin-pack", "ofs-delta")

    def progress(self, message):
        if self.has_capability("no-progress"):
            return
        self.proto.write_sideband(2, message)

    def get_tagged(self, refs=None, repo=None):
        """Get a dict of peeled values of tags to their original tag shas.

        :param refs: dict of refname -> sha of possible tags; defaults to all of
            the backend's refs.
        :param repo: optional Repo instance for getting peeled refs; defaults to
            the backend's repo, if available
        :return: dict of peeled_sha -> tag_sha, where tag_sha is the sha of a
            tag whose peeled value is peeled_sha.
        """
        if not self.has_capability("include-tag"):
            return {}
        if refs is None:
            refs = self.repo.get_refs()
        if repo is None:
            repo = getattr(self.repo, "repo", None)
            if repo is None:
                # Bail if we don't have a Repo available; this is ok since
                # clients must be able to handle if the server doesn't include
                # all relevant tags.
                # TODO: fix behavior when missing
                return {}
        tagged = {}
        for name, sha in refs.iteritems():
            peeled_sha = repo.get_peeled(name)
            if peeled_sha != sha:
                tagged[peeled_sha] = sha
        return tagged

    def handle(self):
        write = lambda x: self.proto.write_sideband(1, x)

        graph_walker = ProtocolGraphWalker(self, self.repo.object_store,
            self.repo.get_peeled)
        objects_iter = self.repo.fetch_objects(
          graph_walker.determine_wants, graph_walker, self.progress,
          get_tagged=self.get_tagged)

        # Did the process short-circuit (e.g. in a stateless RPC call)? Note
        # that the client still expects a 0-object pack in most cases.
        if objects_iter is None:
            return

        self.progress("dul-daemon says what\n")
        self.progress("counting objects: %d, done.\n" % len(objects_iter))
        write_pack_objects(ProtocolFile(None, write), objects_iter)
        self.progress("how was that, then?\n")
        # we are done
        self.proto.write("0000")


def _split_proto_line(line, allowed):
    """Split a line read from the wire.

    :param line: The line read from the wire.
    :param allowed: An iterable of command names that should be allowed.
        Command names not listed below as possible return values will be
        ignored.  If None, any commands from the possible return values are
        allowed.
    :return: a tuple having one of the following forms:
        ('want', obj_id)
        ('have', obj_id)
        ('done', None)
        (None, None)  (for a flush-pkt)

    :raise UnexpectedCommandError: if the line cannot be parsed into one of the
        allowed return values.
    """
    if not line:
        fields = [None]
    else:
        fields = line.rstrip('\n').split(' ', 1)
    command = fields[0]
    if allowed is not None and command not in allowed:
        raise UnexpectedCommandError(command)
    try:
        if len(fields) == 1 and command in ('done', None):
            return (command, None)
        elif len(fields) == 2 and command in ('want', 'have'):
            hex_to_sha(fields[1])
            return tuple(fields)
    except (TypeError, AssertionError), e:
        raise GitProtocolError(e)
    raise GitProtocolError('Received invalid line from client: %s' % line)


class ProtocolGraphWalker(object):
    """A graph walker that knows the git protocol.

    As a graph walker, this class implements ack(), next(), and reset(). It
    also contains some base methods for interacting with the wire and walking
    the commit tree.

    The work of determining which acks to send is passed on to the
    implementation instance stored in _impl. The reason for this is that we do
    not know at object creation time what ack level the protocol requires. A
    call to set_ack_level() is required to set up the implementation, before any
    calls to next() or ack() are made.
    """
    def __init__(self, handler, object_store, get_peeled):
        self.handler = handler
        self.store = object_store
        self.get_peeled = get_peeled
        self.proto = handler.proto
        self.http_req = handler.http_req
        self.advertise_refs = handler.advertise_refs
        self._wants = []
        self._cached = False
        self._cache = []
        self._cache_index = 0
        self._impl = None

    def determine_wants(self, heads):
        """Determine the wants for a set of heads.

        The given heads are advertised to the client, who then specifies which
        refs he wants using 'want' lines. This portion of the protocol is the
        same regardless of ack type, and in fact is used to set the ack type of
        the ProtocolGraphWalker.

        :param heads: a dict of refname->SHA1 to advertise
        :return: a list of SHA1s requested by the client
        """
        if not heads:
            # The repo is empty, so short-circuit the whole process.
            self.proto.write_pkt_line(None)
            return []
        values = set(heads.itervalues())
        if self.advertise_refs or not self.http_req:
            for i, (ref, sha) in enumerate(sorted(heads.iteritems())):
                line = "%s %s" % (sha, ref)
                if not i:
                    line = "%s\x00%s" % (line, self.handler.capability_line())
                self.proto.write_pkt_line("%s\n" % line)
                peeled_sha = self.get_peeled(ref)
                if peeled_sha != sha:
                    self.proto.write_pkt_line('%s %s^{}\n' %
                                              (peeled_sha, ref))

            # i'm done..
            self.proto.write_pkt_line(None)

            if self.advertise_refs:
                return None

        # Now client will sending want want want commands
        want = self.proto.read_pkt_line()
        if not want:
            return []
        line, caps = extract_want_line_capabilities(want)
        self.handler.set_client_capabilities(caps)
        self.set_ack_type(ack_type(caps))
        allowed = ('want', None)
        command, sha = _split_proto_line(line, allowed)

        want_revs = []
        while command != None:
            if sha not in values:
                raise GitProtocolError(
                  'Client wants invalid object %s' % sha)
            want_revs.append(sha)
            command, sha = self.read_proto_line(allowed)

        self.set_wants(want_revs)

        if self.http_req and self.proto.eof():
            # The client may close the socket at this point, expecting a
            # flush-pkt from the server. We might be ready to send a packfile at
            # this point, so we need to explicitly short-circuit in this case.
            return []

        return want_revs

    def ack(self, have_ref):
        return self._impl.ack(have_ref)

    def reset(self):
        self._cached = True
        self._cache_index = 0

    def next(self):
        if not self._cached:
            if not self._impl and self.http_req:
                return None
            return self._impl.next()
        self._cache_index += 1
        if self._cache_index > len(self._cache):
            return None
        return self._cache[self._cache_index]

    def read_proto_line(self, allowed):
        """Read a line from the wire.

        :param allowed: An iterable of command names that should be allowed.
        :return: A tuple of (command, value); see _split_proto_line.
        :raise GitProtocolError: If an error occurred reading the line.
        """
        return _split_proto_line(self.proto.read_pkt_line(), allowed)

    def send_ack(self, sha, ack_type=''):
        if ack_type:
            ack_type = ' %s' % ack_type
        self.proto.write_pkt_line('ACK %s%s\n' % (sha, ack_type))

    def send_nak(self):
        self.proto.write_pkt_line('NAK\n')

    def set_wants(self, wants):
        self._wants = wants

    def _is_satisfied(self, haves, want, earliest):
        """Check whether a want is satisfied by a set of haves.

        A want, typically a branch tip, is "satisfied" only if there exists a
        path back from that want to one of the haves.

        :param haves: A set of commits we know the client has.
        :param want: The want to check satisfaction for.
        :param earliest: A timestamp beyond which the search for haves will be
            terminated, presumably because we're searching too far down the
            wrong branch.
        """
        o = self.store[want]
        pending = collections.deque([o])
        while pending:
            commit = pending.popleft()
            if commit.id in haves:
                return True
            if commit.type_name != "commit":
                # non-commit wants are assumed to be satisfied
                continue
            for parent in commit.parents:
                parent_obj = self.store[parent]
                # TODO: handle parents with later commit times than children
                if parent_obj.commit_time >= earliest:
                    pending.append(parent_obj)
        return False

    def all_wants_satisfied(self, haves):
        """Check whether all the current wants are satisfied by a set of haves.

        :param haves: A set of commits we know the client has.
        :note: Wants are specified with set_wants rather than passed in since
            in the current interface they are determined outside this class.
        """
        haves = set(haves)
        earliest = min([self.store[h].commit_time for h in haves])
        for want in self._wants:
            if not self._is_satisfied(haves, want, earliest):
                return False
        return True

    def set_ack_type(self, ack_type):
        impl_classes = {
          MULTI_ACK: MultiAckGraphWalkerImpl,
          MULTI_ACK_DETAILED: MultiAckDetailedGraphWalkerImpl,
          SINGLE_ACK: SingleAckGraphWalkerImpl,
          }
        self._impl = impl_classes[ack_type](self)


_GRAPH_WALKER_COMMANDS = ('have', 'done', None)


class SingleAckGraphWalkerImpl(object):
    """Graph walker implementation that speaks the single-ack protocol."""

    def __init__(self, walker):
        self.walker = walker
        self._sent_ack = False

    def ack(self, have_ref):
        if not self._sent_ack:
            self.walker.send_ack(have_ref)
            self._sent_ack = True

    def next(self):
        command, sha = self.walker.read_proto_line(_GRAPH_WALKER_COMMANDS)
        if command in (None, 'done'):
            if not self._sent_ack:
                self.walker.send_nak()
            return None
        elif command == 'have':
            return sha


class MultiAckGraphWalkerImpl(object):
    """Graph walker implementation that speaks the multi-ack protocol."""

    def __init__(self, walker):
        self.walker = walker
        self._found_base = False
        self._common = []

    def ack(self, have_ref):
        self._common.append(have_ref)
        if not self._found_base:
            self.walker.send_ack(have_ref, 'continue')
            if self.walker.all_wants_satisfied(self._common):
                self._found_base = True
        # else we blind ack within next

    def next(self):
        while True:
            command, sha = self.walker.read_proto_line(_GRAPH_WALKER_COMMANDS)
            if command is None:
                self.walker.send_nak()
                # in multi-ack mode, a flush-pkt indicates the client wants to
                # flush but more have lines are still coming
                continue
            elif command == 'done':
                # don't nak unless no common commits were found, even if not
                # everything is satisfied
                if self._common:
                    self.walker.send_ack(self._common[-1])
                else:
                    self.walker.send_nak()
                return None
            elif command == 'have':
                if self._found_base:
                    # blind ack
                    self.walker.send_ack(sha, 'continue')
                return sha


class MultiAckDetailedGraphWalkerImpl(object):
    """Graph walker implementation speaking the multi-ack-detailed protocol."""

    def __init__(self, walker):
        self.walker = walker
        self._found_base = False
        self._common = []

    def ack(self, have_ref):
        self._common.append(have_ref)
        if not self._found_base:
            self.walker.send_ack(have_ref, 'common')
            if self.walker.all_wants_satisfied(self._common):
                self._found_base = True
                self.walker.send_ack(have_ref, 'ready')
        # else we blind ack within next

    def next(self):
        while True:
            command, sha = self.walker.read_proto_line(_GRAPH_WALKER_COMMANDS)
            if command is None:
                self.walker.send_nak()
                if self.walker.http_req:
                    return None
                continue
            elif command == 'done':
                # don't nak unless no common commits were found, even if not
                # everything is satisfied
                if self._common:
                    self.walker.send_ack(self._common[-1])
                else:
                    self.walker.send_nak()
                return None
            elif command == 'have':
                if self._found_base:
                    # blind ack; can happen if the client has more requests
                    # inflight
                    self.walker.send_ack(sha, 'ready')
                return sha


class ReceivePackHandler(Handler):
    """Protocol handler for downloading a pack from the client."""

    def __init__(self, backend, args, proto, http_req=None,
                 advertise_refs=False):
        Handler.__init__(self, backend, proto, http_req=http_req)
        self.repo = backend.open_repository(args[0])
        self.advertise_refs = advertise_refs

    @classmethod
    def capabilities(cls):
        return ("report-status", "delete-refs", "side-band-64k")

    def _apply_pack(self, refs):
        all_exceptions = (IOError, OSError, ChecksumMismatch, ApplyDeltaError,
                          AssertionError, socket.error, zlib.error,
                          ObjectFormatException)
        status = []
        will_send_pack = False

        for command in refs:
            if command[1] != ZERO_SHA:
                will_send_pack = True

        if will_send_pack:
            # TODO: more informative error messages than just the exception string
            try:
                recv = getattr(self.proto, "recv", None)
                p = self.repo.object_store.add_thin_pack(self.proto.read, recv)
                status.append(('unpack', 'ok'))
            except all_exceptions, e:
                status.append(('unpack', str(e).replace('\n', '')))
                # The pack may still have been moved in, but it may contain broken
                # objects. We trust a later GC to clean it up.
        else:
            # The git protocol want to find a status entry related to unpack process
            # even if no pack data has been sent.
            status.append(('unpack', 'ok'))

        for oldsha, sha, ref in refs:
            ref_status = 'ok'
            try:
                if sha == ZERO_SHA:
                    if not 'delete-refs' in self.capabilities():
                        raise GitProtocolError(
                          'Attempted to delete refs without delete-refs '
                          'capability.')
                    try:
                        del self.repo.refs[ref]
                    except all_exceptions:
                        ref_status = 'failed to delete'
                else:
                    try:
                        self.repo.refs[ref] = sha
                    except all_exceptions:
                        ref_status = 'failed to write'
            except KeyError, e:
                ref_status = 'bad ref'
            status.append((ref, ref_status))

        return status

    def _report_status(self, status):
        if self.has_capability('side-band-64k'):
            writer = BufferedPktLineWriter(
              lambda d: self.proto.write_sideband(1, d))
            write = writer.write

            def flush():
                writer.flush()
                self.proto.write_pkt_line(None)
        else:
            write = self.proto.write_pkt_line
            flush = lambda: None

        for name, msg in status:
            if name == 'unpack':
                write('unpack %s\n' % msg)
            elif msg == 'ok':
                write('ok %s\n' % name)
            else:
                write('ng %s %s\n' % (name, msg))
        write(None)
        flush()

    def handle(self):
        refs = sorted(self.repo.get_refs().iteritems())

        if self.advertise_refs or not self.http_req:
            if refs:
                self.proto.write_pkt_line(
                  "%s %s\x00%s\n" % (refs[0][1], refs[0][0],
                                     self.capability_line()))
                for i in range(1, len(refs)):
                    ref = refs[i]
                    self.proto.write_pkt_line("%s %s\n" % (ref[1], ref[0]))
            else:
                self.proto.write_pkt_line("%s capabilities^{}\0%s" % (
                  ZERO_SHA, self.capability_line()))

            self.proto.write("0000")
            if self.advertise_refs:
                return

        client_refs = []
        ref = self.proto.read_pkt_line()

        # if ref is none then client doesnt want to send us anything..
        if ref is None:
            return

        ref, caps = extract_capabilities(ref)
        self.set_client_capabilities(caps)

        # client will now send us a list of (oldsha, newsha, ref)
        while ref:
            client_refs.append(ref.split())
            ref = self.proto.read_pkt_line()

        # backend can now deal with this refs and read a pack using self.read
        status = self._apply_pack(client_refs)

        # when we have read all the pack from the client, send a status report
        # if the client asked for it
        if self.has_capability('report-status'):
            self._report_status(status)


# Default handler classes for git services.
DEFAULT_HANDLERS = {
  'git-upload-pack': UploadPackHandler,
  'git-receive-pack': ReceivePackHandler,
  }


class TCPGitRequestHandler(SocketServer.StreamRequestHandler):

    def __init__(self, handlers, *args, **kwargs):
        self.handlers = handlers
        SocketServer.StreamRequestHandler.__init__(self, *args, **kwargs)

    def handle(self):
        proto = ReceivableProtocol(self.connection.recv, self.wfile.write)
        command, args = proto.read_cmd()
        logger.info('Handling %s request, args=%s', command, args)

        cls = self.handlers.get(command, None)
        if not callable(cls):
            raise GitProtocolError('Invalid service %s' % command)
        h = cls(self.server.backend, args, proto)
        h.handle()


class TCPGitServer(SocketServer.TCPServer):

    allow_reuse_address = True
    serve = SocketServer.TCPServer.serve_forever

    def _make_handler(self, *args, **kwargs):
        return TCPGitRequestHandler(self.handlers, *args, **kwargs)

    def __init__(self, backend, listen_addr, port=TCP_GIT_PORT, handlers=None):
        self.handlers = dict(DEFAULT_HANDLERS)
        if handlers is not None:
            self.handlers.update(handlers)
        self.backend = backend
        logger.info('Listening for TCP connections on %s:%d', listen_addr, port)
        SocketServer.TCPServer.__init__(self, (listen_addr, port),
                                        self._make_handler)

    def verify_request(self, request, client_address):
        logger.info('Handling request from %s', client_address)
        return True

    def handle_error(self, request, client_address):
        logger.exception('Exception happened during processing of request '
                         'from %s', client_address)


def main(argv=sys.argv):
    """Entry point for starting a TCP git server."""
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("-b", "--backend", dest="backend",
                      help="Select backend to use.",
                      choices=["file"], default="file")
    options, args = parser.parse_args(argv)

    log_utils.default_logging_config()
    if options.backend == "file":
        if len(argv) > 1:
            gitdir = args[1]
        else:
            gitdir = '.'
        backend = DictBackend({'/': Repo(gitdir)})
    else:
        raise Exception("No such backend %s." % backend)
    server = TCPGitServer(backend, 'localhost')
    server.serve_forever()


def serve_command(handler_cls, argv=sys.argv, backend=None, inf=sys.stdin,
                  outf=sys.stdout):
    """Serve a single command.

    This is mostly useful for the implementation of commands used by e.g. git+ssh.

    :param handler_cls: `Handler` class to use for the request
    :param argv: execv-style command-line arguments. Defaults to sys.argv.
    :param backend: `Backend` to use
    :param inf: File-like object to read from, defaults to standard input.
    :param outf: File-like object to write to, defaults to standard output.
    :return: Exit code for use with sys.exit. 0 on success, 1 on failure.
    """
    if backend is None:
        backend = FileSystemBackend()
    def send_fn(data):
        outf.write(data)
        outf.flush()
    proto = Protocol(inf.read, send_fn)
    handler = handler_cls(backend, argv[1:], proto)
    # FIXME: Catch exceptions and write a single-line summary to outf.
    handler.handle()
    return 0


def generate_info_refs(repo):
    """Generate an info refs file."""
    refs = repo.get_refs()
    for name in sorted(refs.iterkeys()):
        # get_refs() includes HEAD as a special case, but we don't want to
        # advertise it
        if name == 'HEAD':
            continue
        sha = refs[name]
        o = repo.object_store[sha]
        if not o:
            continue
        yield '%s\t%s\n' % (sha, name)
        peeled_sha = repo.get_peeled(name)
        if peeled_sha != sha:
            yield '%s\t%s^{}\n' % (peeled_sha, name)


def generate_objects_info_packs(repo):
    """Generate an index for for packs."""
    for pack in repo.object_store.packs:
        yield 'P pack-%s.pack\n' % pack.name()


def update_server_info(repo):
    """Generate server info for dumb file access.

    This generates info/refs and objects/info/packs,
    similar to "git update-server-info".
    """
    repo._put_named_file(os.path.join('info', 'refs'),
        "".join(generate_info_refs(repo)))

    repo._put_named_file(os.path.join('objects', 'info', 'packs'),
        "".join(generate_objects_info_packs(repo)))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_blackbox
# test_blackbox.py -- blackbox tests
# Copyright (C) 2010 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Blackbox tests for Dulwich commands."""

import tempfile

from dulwich.repo import (
    Repo,
    )
from dulwich.tests import (
    BlackboxTestCase,
    )


class GitReceivePackTests(BlackboxTestCase):
    """Blackbox tests for dul-receive-pack."""

    def setUp(self):
        super(GitReceivePackTests, self).setUp()
        self.path = tempfile.mkdtemp()
        self.repo = Repo.init(self.path)

    def test_basic(self):
        process = self.run_command("dul-receive-pack", [self.path])
        (stdout, stderr) = process.communicate("0000")
        self.assertEqual('', stderr)
        self.assertEqual('0000', stdout[-4:])
        self.assertEqual(0, process.returncode)

    def test_missing_arg(self):
        process = self.run_command("dul-receive-pack", [])
        (stdout, stderr) = process.communicate()
        self.assertEqual('usage: dul-receive-pack <git-dir>\n', stderr)
        self.assertEqual('', stdout)
        self.assertEqual(1, process.returncode)


class GitUploadPackTests(BlackboxTestCase):
    """Blackbox tests for dul-upload-pack."""

    def setUp(self):
        super(GitUploadPackTests, self).setUp()
        self.path = tempfile.mkdtemp()
        self.repo = Repo.init(self.path)

    def test_missing_arg(self):
        process = self.run_command("dul-upload-pack", [])
        (stdout, stderr) = process.communicate()
        self.assertEqual('usage: dul-upload-pack <git-dir>\n', stderr)
        self.assertEqual('', stdout)
        self.assertEqual(1, process.returncode)

########NEW FILE########
__FILENAME__ = test_client
# test_client.py -- Tests for the git protocol, client side
# Copyright (C) 2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

from cStringIO import StringIO

from dulwich import (
    client,
    )
from dulwich.client import (
    TraditionalGitClient,
    TCPGitClient,
    SubprocessGitClient,
    SSHGitClient,
    HttpGitClient,
    ReportStatusParser,
    SendPackError,
    UpdateRefsError,
    get_transport_and_path,
    )
from dulwich.tests import (
    TestCase,
    )
from dulwich.protocol import (
    TCP_GIT_PORT,
    Protocol,
    )
from dulwich.pack import (
    write_pack_objects,
    )
from dulwich.objects import (
    Commit,
    Tree
    )


class DummyClient(TraditionalGitClient):

    def __init__(self, can_read, read, write):
        self.can_read = can_read
        self.read = read
        self.write = write
        TraditionalGitClient.__init__(self)

    def _connect(self, service, path):
        return Protocol(self.read, self.write), self.can_read


# TODO(durin42): add unit-level tests of GitClient
class GitClientTests(TestCase):

    def setUp(self):
        super(GitClientTests, self).setUp()
        self.rout = StringIO()
        self.rin = StringIO()
        self.client = DummyClient(lambda x: True, self.rin.read,
                                  self.rout.write)

    def test_caps(self):
        self.assertEqual(set(['multi_ack', 'side-band-64k', 'ofs-delta',
                               'thin-pack', 'multi_ack_detailed']),
                          set(self.client._fetch_capabilities))
        self.assertEqual(set(['ofs-delta', 'report-status', 'side-band-64k']),
                          set(self.client._send_capabilities))

    def test_archive_ack(self):
        self.rin.write(
            '0009NACK\n'
            '0000')
        self.rin.seek(0)
        self.client.archive('bla', 'HEAD', None, None)
        self.assertEqual(self.rout.getvalue(), '0011argument HEAD0000')

    def test_fetch_empty(self):
        self.rin.write('0000')
        self.rin.seek(0)
        self.client.fetch_pack('/', lambda heads: [], None, None)

    def test_fetch_pack_none(self):
        self.rin.write(
            '008855dcc6bf963f922e1ed5c4bbaaefcfacef57b1d7 HEAD.multi_ack '
            'thin-pack side-band side-band-64k ofs-delta shallow no-progress '
            'include-tag\n'
            '0000')
        self.rin.seek(0)
        self.client.fetch_pack('bla', lambda heads: [], None, None, None)
        self.assertEqual(self.rout.getvalue(), '0000')

    def test_get_transport_and_path_tcp(self):
        client, path = get_transport_and_path('git://foo.com/bar/baz')
        self.assertTrue(isinstance(client, TCPGitClient))
        self.assertEqual('foo.com', client._host)
        self.assertEqual(TCP_GIT_PORT, client._port)
        self.assertEqual('/bar/baz', path)

    def test_get_transport_and_path_tcp_port(self):
        client, path = get_transport_and_path('git://foo.com:1234/bar/baz')
        self.assertTrue(isinstance(client, TCPGitClient))
        self.assertEqual('foo.com', client._host)
        self.assertEqual(1234, client._port)
        self.assertEqual('/bar/baz', path)

    def test_get_transport_and_path_ssh_explicit(self):
        client, path = get_transport_and_path('git+ssh://foo.com/bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo.com', client.host)
        self.assertEqual(None, client.port)
        self.assertEqual(None, client.username)
        self.assertEqual('bar/baz', path)

    def test_get_transport_and_path_ssh_port_explicit(self):
        client, path = get_transport_and_path(
            'git+ssh://foo.com:1234/bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo.com', client.host)
        self.assertEqual(1234, client.port)
        self.assertEqual('bar/baz', path)

    def test_get_transport_and_path_ssh_abspath_explicit(self):
        client, path = get_transport_and_path('git+ssh://foo.com//bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo.com', client.host)
        self.assertEqual(None, client.port)
        self.assertEqual(None, client.username)
        self.assertEqual('/bar/baz', path)

    def test_get_transport_and_path_ssh_port_abspath_explicit(self):
        client, path = get_transport_and_path(
            'git+ssh://foo.com:1234//bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo.com', client.host)
        self.assertEqual(1234, client.port)
        self.assertEqual('/bar/baz', path)

    def test_get_transport_and_path_ssh_implicit(self):
        client, path = get_transport_and_path('foo:/bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo', client.host)
        self.assertEqual(None, client.port)
        self.assertEqual(None, client.username)
        self.assertEqual('/bar/baz', path)

    def test_get_transport_and_path_ssh_host(self):
        client, path = get_transport_and_path('foo.com:/bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo.com', client.host)
        self.assertEqual(None, client.port)
        self.assertEqual(None, client.username)
        self.assertEqual('/bar/baz', path)

    def test_get_transport_and_path_ssh_user_host(self):
        client, path = get_transport_and_path('user@foo.com:/bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo.com', client.host)
        self.assertEqual(None, client.port)
        self.assertEqual('user', client.username)
        self.assertEqual('/bar/baz', path)

    def test_get_transport_and_path_ssh_relpath(self):
        client, path = get_transport_and_path('foo:bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo', client.host)
        self.assertEqual(None, client.port)
        self.assertEqual(None, client.username)
        self.assertEqual('bar/baz', path)

    def test_get_transport_and_path_ssh_host_relpath(self):
        client, path = get_transport_and_path('foo.com:bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo.com', client.host)
        self.assertEqual(None, client.port)
        self.assertEqual(None, client.username)
        self.assertEqual('bar/baz', path)

    def test_get_transport_and_path_ssh_user_host_relpath(self):
        client, path = get_transport_and_path('user@foo.com:bar/baz')
        self.assertTrue(isinstance(client, SSHGitClient))
        self.assertEqual('foo.com', client.host)
        self.assertEqual(None, client.port)
        self.assertEqual('user', client.username)
        self.assertEqual('bar/baz', path)

    def test_get_transport_and_path_subprocess(self):
        client, path = get_transport_and_path('foo.bar/baz')
        self.assertTrue(isinstance(client, SubprocessGitClient))
        self.assertEqual('foo.bar/baz', path)

    def test_get_transport_and_path_error(self):
        # Need to use a known urlparse.uses_netloc URL scheme to get the
        # expected parsing of the URL on Python versions less than 2.6.5
        self.assertRaises(ValueError, get_transport_and_path,
        'prospero://bar/baz')

    def test_get_transport_and_path_http(self):
        url = 'https://github.com/jelmer/dulwich'
        client, path = get_transport_and_path(url)
        self.assertTrue(isinstance(client, HttpGitClient))
        self.assertEqual('/jelmer/dulwich', path)

    def test_send_pack_no_sideband64k_with_update_ref_error(self):
        # No side-bank-64k reported by server shouldn't try to parse
        # side band data
        pkts = ['55dcc6bf963f922e1ed5c4bbaaefcfacef57b1d7 capabilities^{}'
                '\x00 report-status delete-refs ofs-delta\n',
                '',
                "unpack ok",
                "ng refs/foo/bar pre-receive hook declined",
                '']
        for pkt in pkts:
            if pkt == '':
                self.rin.write("0000")
            else:
                self.rin.write("%04x%s" % (len(pkt)+4, pkt))
        self.rin.seek(0)

        tree = Tree()
        commit = Commit()
        commit.tree = tree
        commit.parents = []
        commit.author = commit.committer = 'test user'
        commit.commit_time = commit.author_time = 1174773719
        commit.commit_timezone = commit.author_timezone = 0
        commit.encoding = 'UTF-8'
        commit.message = 'test message'

        def determine_wants(refs):
            return {'refs/foo/bar': commit.id, }

        def generate_pack_contents(have, want):
            return [(commit, None), (tree, ''), ]

        self.assertRaises(UpdateRefsError,
                          self.client.send_pack, "blah",
                          determine_wants, generate_pack_contents)

    def test_send_pack_none(self):
        self.rin.write(
            '0078310ca9477129b8586fa2afc779c1f57cf64bba6c '
            'refs/heads/master\x00 report-status delete-refs '
            'side-band-64k quiet ofs-delta\n'
            '0000')
        self.rin.seek(0)

        def determine_wants(refs):
            return {
                'refs/heads/master': '310ca9477129b8586fa2afc779c1f57cf64bba6c'
            }

        def generate_pack_contents(have, want):
            return {}

        self.client.send_pack('/', determine_wants, generate_pack_contents)
        self.assertEqual(self.rout.getvalue(), '0000')

    def test_send_pack_delete_only(self):
        self.rin.write(
            '0063310ca9477129b8586fa2afc779c1f57cf64bba6c '
            'refs/heads/master\x00report-status delete-refs ofs-delta\n'
            '0000000eunpack ok\n'
            '0019ok refs/heads/master\n'
            '0000')
        self.rin.seek(0)

        def determine_wants(refs):
            return {'refs/heads/master': '0' * 40}

        def generate_pack_contents(have, want):
            return {}

        self.client.send_pack('/', determine_wants, generate_pack_contents)
        self.assertEqual(
            self.rout.getvalue(),
            '007f310ca9477129b8586fa2afc779c1f57cf64bba6c '
            '0000000000000000000000000000000000000000 '
            'refs/heads/master\x00report-status ofs-delta0000')

    def test_send_pack_new_ref_only(self):
        self.rin.write(
            '0063310ca9477129b8586fa2afc779c1f57cf64bba6c '
            'refs/heads/master\x00report-status delete-refs ofs-delta\n'
            '0000000eunpack ok\n'
            '0019ok refs/heads/blah12\n'
            '0000')
        self.rin.seek(0)

        def determine_wants(refs):
            return {
                'refs/heads/blah12':
                '310ca9477129b8586fa2afc779c1f57cf64bba6c',
                'refs/heads/master': '310ca9477129b8586fa2afc779c1f57cf64bba6c'
            }

        def generate_pack_contents(have, want):
            return {}

        f = StringIO()
        empty_pack = write_pack_objects(f, {})
        self.client.send_pack('/', determine_wants, generate_pack_contents)
        self.assertEqual(
            self.rout.getvalue(),
            '007f0000000000000000000000000000000000000000 '
            '310ca9477129b8586fa2afc779c1f57cf64bba6c '
            'refs/heads/blah12\x00report-status ofs-delta0000%s'
            % f.getvalue())

    def test_send_pack_new_ref(self):
        self.rin.write(
            '0064310ca9477129b8586fa2afc779c1f57cf64bba6c '
            'refs/heads/master\x00 report-status delete-refs ofs-delta\n'
            '0000000eunpack ok\n'
            '0019ok refs/heads/blah12\n'
            '0000')
        self.rin.seek(0)

        tree = Tree()
        commit = Commit()
        commit.tree = tree
        commit.parents = []
        commit.author = commit.committer = 'test user'
        commit.commit_time = commit.author_time = 1174773719
        commit.commit_timezone = commit.author_timezone = 0
        commit.encoding = 'UTF-8'
        commit.message = 'test message'

        def determine_wants(refs):
            return {
                'refs/heads/blah12': commit.id,
                'refs/heads/master': '310ca9477129b8586fa2afc779c1f57cf64bba6c'
            }

        def generate_pack_contents(have, want):
            return [(commit, None), (tree, ''), ]

        f = StringIO()
        pack = write_pack_objects(f, generate_pack_contents(None, None))
        self.client.send_pack('/', determine_wants, generate_pack_contents)
        self.assertEqual(
            self.rout.getvalue(),
            '007f0000000000000000000000000000000000000000 %s '
            'refs/heads/blah12\x00report-status ofs-delta0000%s'
            % (commit.id, f.getvalue()))

    def test_send_pack_no_deleteref_delete_only(self):
        pkts = ['310ca9477129b8586fa2afc779c1f57cf64bba6c refs/heads/master'
                '\x00 report-status ofs-delta\n',
                '',
                '']
        for pkt in pkts:
            if pkt == '':
                self.rin.write("0000")
            else:
                self.rin.write("%04x%s" % (len(pkt)+4, pkt))
        self.rin.seek(0)

        def determine_wants(refs):
            return {'refs/heads/master': '0' * 40}

        def generate_pack_contents(have, want):
            return {}

        self.assertRaises(UpdateRefsError,
                          self.client.send_pack, "/",
                          determine_wants, generate_pack_contents)
        self.assertEqual(self.rout.getvalue(), '0000')


class TestSSHVendor(object):

    def __init__(self):
        self.host = None
        self.command = ""
        self.username = None
        self.port = None

    def run_command(self, host, command, username=None, port=None):
        self.host = host
        self.command = command
        self.username = username
        self.port = port

        class Subprocess: pass
        setattr(Subprocess, 'read', lambda: None)
        setattr(Subprocess, 'write', lambda: None)
        setattr(Subprocess, 'can_read', lambda: None)
        return Subprocess()


class SSHGitClientTests(TestCase):

    def setUp(self):
        super(SSHGitClientTests, self).setUp()

        self.server = TestSSHVendor()
        self.real_vendor = client.get_ssh_vendor
        client.get_ssh_vendor = lambda: self.server

        self.client = SSHGitClient('git.samba.org')

    def tearDown(self):
        super(SSHGitClientTests, self).tearDown()
        client.get_ssh_vendor = self.real_vendor

    def test_default_command(self):
        self.assertEqual('git-upload-pack',
                self.client._get_cmd_path('upload-pack'))

    def test_alternative_command_path(self):
        self.client.alternative_paths['upload-pack'] = (
            '/usr/lib/git/git-upload-pack')
        self.assertEqual('/usr/lib/git/git-upload-pack',
            self.client._get_cmd_path('upload-pack'))

    def test_connect(self):
        server = self.server
        client = self.client

        client.username = "username"
        client.port = 1337

        client._connect("command", "/path/to/repo")
        self.assertEquals("username", server.username)
        self.assertEquals(1337, server.port)
        self.assertEquals(["git-command '/path/to/repo'"], server.command)

        client._connect("relative-command", "/~/path/to/repo")
        self.assertEquals(["git-relative-command '~/path/to/repo'"],
                          server.command)

class ReportStatusParserTests(TestCase):

    def test_invalid_pack(self):
        parser = ReportStatusParser()
        parser.handle_packet("unpack error - foo bar")
        parser.handle_packet("ok refs/foo/bar")
        parser.handle_packet(None)
        self.assertRaises(SendPackError, parser.check)

    def test_update_refs_error(self):
        parser = ReportStatusParser()
        parser.handle_packet("unpack ok")
        parser.handle_packet("ng refs/foo/bar need to pull")
        parser.handle_packet(None)
        self.assertRaises(UpdateRefsError, parser.check)

    def test_ok(self):
        parser = ReportStatusParser()
        parser.handle_packet("unpack ok")
        parser.handle_packet("ok refs/foo/bar")
        parser.handle_packet(None)
        parser.check()

########NEW FILE########
__FILENAME__ = test_config
# test_config.py -- Tests for reading and writing configuration files
# Copyright (C) 2011 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for reading and writing configuration files."""

from cStringIO import StringIO
from dulwich.config import (
    ConfigDict,
    ConfigFile,
    StackedConfig,
    _check_section_name,
    _check_variable_name,
    _format_string,
    _escape_value,
    _parse_string,
    _unescape_value,
    )
from dulwich.tests import TestCase


class ConfigFileTests(TestCase):

    def from_file(self, text):
        return ConfigFile.from_file(StringIO(text))

    def test_empty(self):
        ConfigFile()

    def test_eq(self):
        self.assertEqual(ConfigFile(), ConfigFile())

    def test_default_config(self):
        cf = self.from_file("""[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
	logallrefupdates = true
""")
        self.assertEqual(ConfigFile({("core", ): {
            "repositoryformatversion": "0",
            "filemode": "true",
            "bare": "false",
            "logallrefupdates": "true"}}), cf)

    def test_from_file_empty(self):
        cf = self.from_file("")
        self.assertEqual(ConfigFile(), cf)

    def test_empty_line_before_section(self):
        cf = self.from_file("\n[section]\n")
        self.assertEqual(ConfigFile({("section", ): {}}), cf)

    def test_comment_before_section(self):
        cf = self.from_file("# foo\n[section]\n")
        self.assertEqual(ConfigFile({("section", ): {}}), cf)

    def test_comment_after_section(self):
        cf = self.from_file("[section] # foo\n")
        self.assertEqual(ConfigFile({("section", ): {}}), cf)

    def test_comment_after_variable(self):
        cf = self.from_file("[section]\nbar= foo # a comment\n")
        self.assertEqual(ConfigFile({("section", ): {"bar": "foo"}}), cf)

    def test_from_file_section(self):
        cf = self.from_file("[core]\nfoo = bar\n")
        self.assertEqual("bar", cf.get(("core", ), "foo"))
        self.assertEqual("bar", cf.get(("core", "foo"), "foo"))

    def test_from_file_section_case_insensitive(self):
        cf = self.from_file("[cOre]\nfOo = bar\n")
        self.assertEqual("bar", cf.get(("core", ), "foo"))
        self.assertEqual("bar", cf.get(("core", "foo"), "foo"))

    def test_from_file_with_mixed_quoted(self):
        cf = self.from_file("[core]\nfoo = \"bar\"la\n")
        self.assertEqual("barla", cf.get(("core", ), "foo"))

    def test_from_file_with_open_quoted(self):
        self.assertRaises(ValueError,
            self.from_file, "[core]\nfoo = \"bar\n")

    def test_from_file_with_quotes(self):
        cf = self.from_file(
            "[core]\n"
            'foo = " bar"\n')
        self.assertEqual(" bar", cf.get(("core", ), "foo"))

    def test_from_file_with_interrupted_line(self):
        cf = self.from_file(
            "[core]\n"
            'foo = bar\\\n'
            ' la\n')
        self.assertEqual("barla", cf.get(("core", ), "foo"))

    def test_from_file_with_boolean_setting(self):
        cf = self.from_file(
            "[core]\n"
            'foo\n')
        self.assertEqual("true", cf.get(("core", ), "foo"))

    def test_from_file_subsection(self):
        cf = self.from_file("[branch \"foo\"]\nfoo = bar\n")
        self.assertEqual("bar", cf.get(("branch", "foo"), "foo"))

    def test_from_file_subsection_invalid(self):
        self.assertRaises(ValueError,
            self.from_file, "[branch \"foo]\nfoo = bar\n")

    def test_from_file_subsection_not_quoted(self):
        cf = self.from_file("[branch.foo]\nfoo = bar\n")
        self.assertEqual("bar", cf.get(("branch", "foo"), "foo"))

    def test_write_to_file_empty(self):
        c = ConfigFile()
        f = StringIO()
        c.write_to_file(f)
        self.assertEqual("", f.getvalue())

    def test_write_to_file_section(self):
        c = ConfigFile()
        c.set(("core", ), "foo", "bar")
        f = StringIO()
        c.write_to_file(f)
        self.assertEqual("[core]\n\tfoo = bar\n", f.getvalue())

    def test_write_to_file_subsection(self):
        c = ConfigFile()
        c.set(("branch", "blie"), "foo", "bar")
        f = StringIO()
        c.write_to_file(f)
        self.assertEqual("[branch \"blie\"]\n\tfoo = bar\n", f.getvalue())

    def test_same_line(self):
        cf = self.from_file("[branch.foo] foo = bar\n")
        self.assertEqual("bar", cf.get(("branch", "foo"), "foo"))


class ConfigDictTests(TestCase):

    def test_get_set(self):
        cd = ConfigDict()
        self.assertRaises(KeyError, cd.get, "foo", "core")
        cd.set(("core", ), "foo", "bla")
        self.assertEqual("bla", cd.get(("core", ), "foo"))
        cd.set(("core", ), "foo", "bloe")
        self.assertEqual("bloe", cd.get(("core", ), "foo"))

    def test_get_boolean(self):
        cd = ConfigDict()
        cd.set(("core", ), "foo", "true")
        self.assertTrue(cd.get_boolean(("core", ), "foo"))
        cd.set(("core", ), "foo", "false")
        self.assertFalse(cd.get_boolean(("core", ), "foo"))
        cd.set(("core", ), "foo", "invalid")
        self.assertRaises(ValueError, cd.get_boolean, ("core", ), "foo")

    def test_dict(self):
        cd = ConfigDict()
        cd.set(("core", ), "foo", "bla")
        cd.set(("core2", ), "foo", "bloe")

        self.assertEqual([("core", ), ("core2", )], cd.keys())
        self.assertEqual(cd[("core", )], {'foo': 'bla'})

        cd['a'] = 'b'
        self.assertEqual(cd['a'], 'b')


class StackedConfigTests(TestCase):

    def test_default_backends(self):
        StackedConfig.default_backends()


class UnescapeTests(TestCase):

    def test_nothing(self):
        self.assertEqual("", _unescape_value(""))

    def test_tab(self):
        self.assertEqual("\tbar\t", _unescape_value("\\tbar\\t"))

    def test_newline(self):
        self.assertEqual("\nbar\t", _unescape_value("\\nbar\\t"))

    def test_quote(self):
        self.assertEqual("\"foo\"", _unescape_value("\\\"foo\\\""))


class EscapeValueTests(TestCase):

    def test_nothing(self):
        self.assertEqual("foo", _escape_value("foo"))

    def test_backslash(self):
        self.assertEqual("foo\\\\", _escape_value("foo\\"))

    def test_newline(self):
        self.assertEqual("foo\\n", _escape_value("foo\n"))


class FormatStringTests(TestCase):

    def test_quoted(self):
        self.assertEqual('" foo"', _format_string(" foo"))
        self.assertEqual('"\\tfoo"', _format_string("\tfoo"))

    def test_not_quoted(self):
        self.assertEqual('foo', _format_string("foo"))
        self.assertEqual('foo bar', _format_string("foo bar"))


class ParseStringTests(TestCase):

    def test_quoted(self):
        self.assertEqual(' foo', _parse_string('" foo"'))
        self.assertEqual('\tfoo', _parse_string('"\\tfoo"'))

    def test_not_quoted(self):
        self.assertEqual('foo', _parse_string("foo"))
        self.assertEqual('foo bar', _parse_string("foo bar"))


class CheckVariableNameTests(TestCase):

    def test_invalid(self):
        self.assertFalse(_check_variable_name("foo "))
        self.assertFalse(_check_variable_name("bar,bar"))
        self.assertFalse(_check_variable_name("bar.bar"))

    def test_valid(self):
        self.assertTrue(_check_variable_name("FOO"))
        self.assertTrue(_check_variable_name("foo"))
        self.assertTrue(_check_variable_name("foo-bar"))


class CheckSectionNameTests(TestCase):

    def test_invalid(self):
        self.assertFalse(_check_section_name("foo "))
        self.assertFalse(_check_section_name("bar,bar"))

    def test_valid(self):
        self.assertTrue(_check_section_name("FOO"))
        self.assertTrue(_check_section_name("foo"))
        self.assertTrue(_check_section_name("foo-bar"))
        self.assertTrue(_check_section_name("bar.bar"))

########NEW FILE########
__FILENAME__ = test_diff_tree
# test_diff_tree.py -- Tests for file and tree diff utilities.
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for file and tree diff utilities."""

from dulwich.diff_tree import (
    CHANGE_MODIFY,
    CHANGE_RENAME,
    CHANGE_COPY,
    CHANGE_UNCHANGED,
    TreeChange,
    _merge_entries,
    _merge_entries_py,
    tree_changes,
    tree_changes_for_merge,
    _count_blocks,
    _count_blocks_py,
    _similarity_score,
    _tree_change_key,
    RenameDetector,
    _is_tree,
    _is_tree_py
    )
from dulwich.index import (
    commit_tree,
    )
from dulwich._compat import (
    permutations,
    )
from dulwich.object_store import (
    MemoryObjectStore,
    )
from dulwich.objects import (
    ShaFile,
    Blob,
    TreeEntry,
    Tree,
    )
from dulwich.tests import (
    TestCase,
    )
from dulwich.tests.utils import (
    F,
    make_object,
    functest_builder,
    ext_functest_builder,
    )


class DiffTestCase(TestCase):

    def setUp(self):
        super(DiffTestCase, self).setUp()
        self.store = MemoryObjectStore()
        self.empty_tree = self.commit_tree([])

    def commit_tree(self, entries):
        commit_blobs = []
        for entry in entries:
            if len(entry) == 2:
                path, obj = entry
                mode = F
            else:
                path, obj, mode = entry
            if isinstance(obj, Blob):
                self.store.add_object(obj)
                sha = obj.id
            else:
                sha = obj
            commit_blobs.append((path, sha, mode))
        return self.store[commit_tree(self.store, commit_blobs)]


class TreeChangesTest(DiffTestCase):

    def setUp(self):
        super(TreeChangesTest, self).setUp()
        self.detector = RenameDetector(self.store)

    def assertMergeFails(self, merge_entries, name, mode, sha):
        t = Tree()
        t[name] = (mode, sha)
        self.assertRaises(TypeError, merge_entries, '', t, t)

    def _do_test_merge_entries(self, merge_entries):
        blob_a1 = make_object(Blob, data='a1')
        blob_a2 = make_object(Blob, data='a2')
        blob_b1 = make_object(Blob, data='b1')
        blob_c2 = make_object(Blob, data='c2')
        tree1 = self.commit_tree([('a', blob_a1, 0100644),
                                  ('b', blob_b1, 0100755)])
        tree2 = self.commit_tree([('a', blob_a2, 0100644),
                                  ('c', blob_c2, 0100755)])

        self.assertEqual([], merge_entries('', self.empty_tree,
                                           self.empty_tree))
        self.assertEqual([
          ((None, None, None), ('a', 0100644, blob_a1.id)),
          ((None, None, None), ('b', 0100755, blob_b1.id)),
          ], merge_entries('', self.empty_tree, tree1))
        self.assertEqual([
          ((None, None, None), ('x/a', 0100644, blob_a1.id)),
          ((None, None, None), ('x/b', 0100755, blob_b1.id)),
          ], merge_entries('x', self.empty_tree, tree1))

        self.assertEqual([
          (('a', 0100644, blob_a2.id), (None, None, None)),
          (('c', 0100755, blob_c2.id), (None, None, None)),
          ], merge_entries('', tree2, self.empty_tree))

        self.assertEqual([
          (('a', 0100644, blob_a1.id), ('a', 0100644, blob_a2.id)),
          (('b', 0100755, blob_b1.id), (None, None, None)),
          ((None, None, None), ('c', 0100755, blob_c2.id)),
          ], merge_entries('', tree1, tree2))

        self.assertEqual([
          (('a', 0100644, blob_a2.id), ('a', 0100644, blob_a1.id)),
          ((None, None, None), ('b', 0100755, blob_b1.id)),
          (('c', 0100755, blob_c2.id), (None, None, None)),
          ], merge_entries('', tree2, tree1))

        self.assertMergeFails(merge_entries, 0xdeadbeef, 0100644, '1' * 40)
        self.assertMergeFails(merge_entries, 'a', 'deadbeef', '1' * 40)
        self.assertMergeFails(merge_entries, 'a', 0100644, 0xdeadbeef)

    test_merge_entries = functest_builder(_do_test_merge_entries,
                                          _merge_entries_py)
    test_merge_entries_extension = ext_functest_builder(_do_test_merge_entries,
                                                        _merge_entries)

    def _do_test_is_tree(self, is_tree):
        self.assertFalse(is_tree(TreeEntry(None, None, None)))
        self.assertFalse(is_tree(TreeEntry('a', 0100644, 'a' * 40)))
        self.assertFalse(is_tree(TreeEntry('a', 0100755, 'a' * 40)))
        self.assertFalse(is_tree(TreeEntry('a', 0120000, 'a' * 40)))
        self.assertTrue(is_tree(TreeEntry('a', 0040000, 'a' * 40)))
        self.assertRaises(TypeError, is_tree, TreeEntry('a', 'x', 'a' * 40))
        self.assertRaises(AttributeError, is_tree, 1234)

    test_is_tree = functest_builder(_do_test_is_tree, _is_tree_py)
    test_is_tree_extension = ext_functest_builder(_do_test_is_tree, _is_tree)

    def assertChangesEqual(self, expected, tree1, tree2, **kwargs):
        actual = list(tree_changes(self.store, tree1.id, tree2.id, **kwargs))
        self.assertEqual(expected, actual)

    # For brevity, the following tests use tuples instead of TreeEntry objects.

    def test_tree_changes_empty(self):
        self.assertChangesEqual([], self.empty_tree, self.empty_tree)

    def test_tree_changes_no_changes(self):
        blob = make_object(Blob, data='blob')
        tree = self.commit_tree([('a', blob), ('b/c', blob)])
        self.assertChangesEqual([], self.empty_tree, self.empty_tree)
        self.assertChangesEqual([], tree, tree)
        self.assertChangesEqual(
          [TreeChange(CHANGE_UNCHANGED, ('a', F, blob.id), ('a', F, blob.id)),
           TreeChange(CHANGE_UNCHANGED, ('b/c', F, blob.id),
                      ('b/c', F, blob.id))],
          tree, tree, want_unchanged=True)

    def test_tree_changes_add_delete(self):
        blob_a = make_object(Blob, data='a')
        blob_b = make_object(Blob, data='b')
        tree = self.commit_tree([('a', blob_a, 0100644),
                                 ('x/b', blob_b, 0100755)])
        self.assertChangesEqual(
          [TreeChange.add(('a', 0100644, blob_a.id)),
           TreeChange.add(('x/b', 0100755, blob_b.id))],
          self.empty_tree, tree)
        self.assertChangesEqual(
          [TreeChange.delete(('a', 0100644, blob_a.id)),
           TreeChange.delete(('x/b', 0100755, blob_b.id))],
          tree, self.empty_tree)

    def test_tree_changes_modify_contents(self):
        blob_a1 = make_object(Blob, data='a1')
        blob_a2 = make_object(Blob, data='a2')
        tree1 = self.commit_tree([('a', blob_a1)])
        tree2 = self.commit_tree([('a', blob_a2)])
        self.assertChangesEqual(
          [TreeChange(CHANGE_MODIFY, ('a', F, blob_a1.id),
                      ('a', F, blob_a2.id))], tree1, tree2)

    def test_tree_changes_modify_mode(self):
        blob_a = make_object(Blob, data='a')
        tree1 = self.commit_tree([('a', blob_a, 0100644)])
        tree2 = self.commit_tree([('a', blob_a, 0100755)])
        self.assertChangesEqual(
          [TreeChange(CHANGE_MODIFY, ('a', 0100644, blob_a.id),
                      ('a', 0100755, blob_a.id))], tree1, tree2)

    def test_tree_changes_change_type(self):
        blob_a1 = make_object(Blob, data='a')
        blob_a2 = make_object(Blob, data='/foo/bar')
        tree1 = self.commit_tree([('a', blob_a1, 0100644)])
        tree2 = self.commit_tree([('a', blob_a2, 0120000)])
        self.assertChangesEqual(
          [TreeChange.delete(('a', 0100644, blob_a1.id)),
           TreeChange.add(('a', 0120000, blob_a2.id))],
          tree1, tree2)

    def test_tree_changes_to_tree(self):
        blob_a = make_object(Blob, data='a')
        blob_x = make_object(Blob, data='x')
        tree1 = self.commit_tree([('a', blob_a)])
        tree2 = self.commit_tree([('a/x', blob_x)])
        self.assertChangesEqual(
          [TreeChange.delete(('a', F, blob_a.id)),
           TreeChange.add(('a/x', F, blob_x.id))],
          tree1, tree2)

    def test_tree_changes_complex(self):
        blob_a_1 = make_object(Blob, data='a1_1')
        blob_bx1_1 = make_object(Blob, data='bx1_1')
        blob_bx2_1 = make_object(Blob, data='bx2_1')
        blob_by1_1 = make_object(Blob, data='by1_1')
        blob_by2_1 = make_object(Blob, data='by2_1')
        tree1 = self.commit_tree([
          ('a', blob_a_1),
          ('b/x/1', blob_bx1_1),
          ('b/x/2', blob_bx2_1),
          ('b/y/1', blob_by1_1),
          ('b/y/2', blob_by2_1),
          ])

        blob_a_2 = make_object(Blob, data='a1_2')
        blob_bx1_2 = blob_bx1_1
        blob_by_2 = make_object(Blob, data='by_2')
        blob_c_2 = make_object(Blob, data='c_2')
        tree2 = self.commit_tree([
          ('a', blob_a_2),
          ('b/x/1', blob_bx1_2),
          ('b/y', blob_by_2),
          ('c', blob_c_2),
          ])

        self.assertChangesEqual(
          [TreeChange(CHANGE_MODIFY, ('a', F, blob_a_1.id),
                      ('a', F, blob_a_2.id)),
           TreeChange.delete(('b/x/2', F, blob_bx2_1.id)),
           TreeChange.add(('b/y', F, blob_by_2.id)),
           TreeChange.delete(('b/y/1', F, blob_by1_1.id)),
           TreeChange.delete(('b/y/2', F, blob_by2_1.id)),
           TreeChange.add(('c', F, blob_c_2.id))],
          tree1, tree2)

    def test_tree_changes_name_order(self):
        blob = make_object(Blob, data='a')
        tree1 = self.commit_tree([('a', blob), ('a.', blob), ('a..', blob)])
        # Tree order is the reverse of this, so if we used tree order, 'a..'
        # would not be merged.
        tree2 = self.commit_tree([('a/x', blob), ('a./x', blob), ('a..', blob)])

        self.assertChangesEqual(
          [TreeChange.delete(('a', F, blob.id)),
           TreeChange.add(('a/x', F, blob.id)),
           TreeChange.delete(('a.', F, blob.id)),
           TreeChange.add(('a./x', F, blob.id))],
          tree1, tree2)

    def test_tree_changes_prune(self):
        blob_a1 = make_object(Blob, data='a1')
        blob_a2 = make_object(Blob, data='a2')
        blob_x = make_object(Blob, data='x')
        tree1 = self.commit_tree([('a', blob_a1), ('b/x', blob_x)])
        tree2 = self.commit_tree([('a', blob_a2), ('b/x', blob_x)])
        # Remove identical items so lookups will fail unless we prune.
        subtree = self.store[tree1['b'][1]]
        for entry in subtree.iteritems():
            del self.store[entry.sha]
        del self.store[subtree.id]

        self.assertChangesEqual(
          [TreeChange(CHANGE_MODIFY, ('a', F, blob_a1.id),
                      ('a', F, blob_a2.id))],
          tree1, tree2)

    def test_tree_changes_rename_detector(self):
        blob_a1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob_a2 = make_object(Blob, data='a\nb\nc\ne\n')
        blob_b = make_object(Blob, data='b')
        tree1 = self.commit_tree([('a', blob_a1), ('b', blob_b)])
        tree2 = self.commit_tree([('c', blob_a2), ('b', blob_b)])
        detector = RenameDetector(self.store)

        self.assertChangesEqual(
          [TreeChange.delete(('a', F, blob_a1.id)),
           TreeChange.add(('c', F, blob_a2.id))],
          tree1, tree2)
        self.assertChangesEqual(
          [TreeChange.delete(('a', F, blob_a1.id)),
           TreeChange(CHANGE_UNCHANGED, ('b', F, blob_b.id),
                      ('b', F, blob_b.id)),
           TreeChange.add(('c', F, blob_a2.id))],
          tree1, tree2, want_unchanged=True)
        self.assertChangesEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob_a1.id),
                      ('c', F, blob_a2.id))],
          tree1, tree2, rename_detector=detector)
        self.assertChangesEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob_a1.id),
                      ('c', F, blob_a2.id)),
           TreeChange(CHANGE_UNCHANGED, ('b', F, blob_b.id),
                      ('b', F, blob_b.id))],
          tree1, tree2, rename_detector=detector, want_unchanged=True)

    def assertChangesForMergeEqual(self, expected, parent_trees, merge_tree,
                                   **kwargs):
        parent_tree_ids = [t.id for t in parent_trees]
        actual = list(tree_changes_for_merge(
          self.store, parent_tree_ids, merge_tree.id, **kwargs))
        self.assertEqual(expected, actual)

        parent_tree_ids.reverse()
        expected = [list(reversed(cs)) for cs in expected]
        actual = list(tree_changes_for_merge(
          self.store, parent_tree_ids, merge_tree.id, **kwargs))
        self.assertEqual(expected, actual)

    def test_tree_changes_for_merge_add_no_conflict(self):
        blob = make_object(Blob, data='blob')
        parent1 = self.commit_tree([])
        parent2 = merge = self.commit_tree([('a', blob)])
        self.assertChangesForMergeEqual([], [parent1, parent2], merge)
        self.assertChangesForMergeEqual([], [parent2, parent2], merge)

    def test_tree_changes_for_merge_add_modify_conflict(self):
        blob1 = make_object(Blob, data='1')
        blob2 = make_object(Blob, data='2')
        parent1 = self.commit_tree([])
        parent2 = self.commit_tree([('a', blob1)])
        merge = self.commit_tree([('a', blob2)])
        self.assertChangesForMergeEqual(
          [[TreeChange.add(('a', F, blob2.id)),
            TreeChange(CHANGE_MODIFY, ('a', F, blob1.id), ('a', F, blob2.id))]],
          [parent1, parent2], merge)

    def test_tree_changes_for_merge_modify_modify_conflict(self):
        blob1 = make_object(Blob, data='1')
        blob2 = make_object(Blob, data='2')
        blob3 = make_object(Blob, data='3')
        parent1 = self.commit_tree([('a', blob1)])
        parent2 = self.commit_tree([('a', blob2)])
        merge = self.commit_tree([('a', blob3)])
        self.assertChangesForMergeEqual(
          [[TreeChange(CHANGE_MODIFY, ('a', F, blob1.id), ('a', F, blob3.id)),
            TreeChange(CHANGE_MODIFY, ('a', F, blob2.id), ('a', F, blob3.id))]],
          [parent1, parent2], merge)

    def test_tree_changes_for_merge_modify_no_conflict(self):
        blob1 = make_object(Blob, data='1')
        blob2 = make_object(Blob, data='2')
        parent1 = self.commit_tree([('a', blob1)])
        parent2 = merge = self.commit_tree([('a', blob2)])
        self.assertChangesForMergeEqual([], [parent1, parent2], merge)

    def test_tree_changes_for_merge_delete_delete_conflict(self):
        blob1 = make_object(Blob, data='1')
        blob2 = make_object(Blob, data='2')
        parent1 = self.commit_tree([('a', blob1)])
        parent2 = self.commit_tree([('a', blob2)])
        merge = self.commit_tree([])
        self.assertChangesForMergeEqual(
          [[TreeChange.delete(('a', F, blob1.id)),
            TreeChange.delete(('a', F, blob2.id))]],
          [parent1, parent2], merge)

    def test_tree_changes_for_merge_delete_no_conflict(self):
        blob = make_object(Blob, data='blob')
        has = self.commit_tree([('a', blob)])
        doesnt_have = self.commit_tree([])
        self.assertChangesForMergeEqual([], [has, has], doesnt_have)
        self.assertChangesForMergeEqual([], [has, doesnt_have], doesnt_have)

    def test_tree_changes_for_merge_octopus_no_conflict(self):
        r = range(5)
        blobs = [make_object(Blob, data=str(i)) for i in r]
        parents = [self.commit_tree([('a', blobs[i])]) for i in r]
        for i in r:
            # Take the SHA from each of the parents.
            self.assertChangesForMergeEqual([], parents, parents[i])

    def test_tree_changes_for_merge_octopus_modify_conflict(self):
        # Because the octopus merge strategy is limited, I doubt it's possible
        # to create this with the git command line. But the output is well-
        # defined, so test it anyway.
        r = range(5)
        parent_blobs = [make_object(Blob, data=str(i)) for i in r]
        merge_blob = make_object(Blob, data='merge')
        parents = [self.commit_tree([('a', parent_blobs[i])]) for i in r]
        merge = self.commit_tree([('a', merge_blob)])
        expected = [[TreeChange(CHANGE_MODIFY, ('a', F, parent_blobs[i].id),
                                ('a', F, merge_blob.id)) for i in r]]
        self.assertChangesForMergeEqual(expected, parents, merge)

    def test_tree_changes_for_merge_octopus_delete(self):
        blob1 = make_object(Blob, data='1')
        blob2 = make_object(Blob, data='3')
        parent1 = self.commit_tree([('a', blob1)])
        parent2 = self.commit_tree([('a', blob2)])
        parent3 = merge = self.commit_tree([])
        self.assertChangesForMergeEqual([], [parent1, parent1, parent1], merge)
        self.assertChangesForMergeEqual([], [parent1, parent1, parent3], merge)
        self.assertChangesForMergeEqual([], [parent1, parent3, parent3], merge)
        self.assertChangesForMergeEqual(
          [[TreeChange.delete(('a', F, blob1.id)),
            TreeChange.delete(('a', F, blob2.id)),
            None]],
          [parent1, parent2, parent3], merge)

    def test_tree_changes_for_merge_add_add_same_conflict(self):
        blob = make_object(Blob, data='a\nb\nc\nd\n')
        parent1 = self.commit_tree([('a', blob)])
        parent2 = self.commit_tree([])
        merge = self.commit_tree([('b', blob)])
        add = TreeChange.add(('b', F, blob.id))
        self.assertChangesForMergeEqual([[add, add]], [parent1, parent2], merge)

    def test_tree_changes_for_merge_add_exact_rename_conflict(self):
        blob = make_object(Blob, data='a\nb\nc\nd\n')
        parent1 = self.commit_tree([('a', blob)])
        parent2 = self.commit_tree([])
        merge = self.commit_tree([('b', blob)])
        self.assertChangesForMergeEqual(
          [[TreeChange(CHANGE_RENAME, ('a', F, blob.id), ('b', F, blob.id)),
            TreeChange.add(('b', F, blob.id))]],
          [parent1, parent2], merge, rename_detector=self.detector)

    def test_tree_changes_for_merge_add_content_rename_conflict(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob2 = make_object(Blob, data='a\nb\nc\ne\n')
        parent1 = self.commit_tree([('a', blob1)])
        parent2 = self.commit_tree([])
        merge = self.commit_tree([('b', blob2)])
        self.assertChangesForMergeEqual(
          [[TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('b', F, blob2.id)),
            TreeChange.add(('b', F, blob2.id))]],
          [parent1, parent2], merge, rename_detector=self.detector)

    def test_tree_changes_for_merge_modify_rename_conflict(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob2 = make_object(Blob, data='a\nb\nc\ne\n')
        parent1 = self.commit_tree([('a', blob1)])
        parent2 = self.commit_tree([('b', blob1)])
        merge = self.commit_tree([('b', blob2)])
        self.assertChangesForMergeEqual(
          [[TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('b', F, blob2.id)),
            TreeChange(CHANGE_MODIFY, ('b', F, blob1.id), ('b', F, blob2.id))]],
          [parent1, parent2], merge, rename_detector=self.detector)


class RenameDetectionTest(DiffTestCase):

    def _do_test_count_blocks(self, count_blocks):
        blob = make_object(Blob, data='a\nb\na\n')
        self.assertEqual({hash('a\n'): 4, hash('b\n'): 2}, count_blocks(blob))

    test_count_blocks = functest_builder(_do_test_count_blocks,
                                         _count_blocks_py)
    test_count_blocks_extension = ext_functest_builder(_do_test_count_blocks,
                                                       _count_blocks)

    def _do_test_count_blocks_no_newline(self, count_blocks):
        blob = make_object(Blob, data='a\na')
        self.assertEqual({hash('a\n'): 2, hash('a'): 1}, _count_blocks(blob))

    test_count_blocks_no_newline = functest_builder(
      _do_test_count_blocks_no_newline, _count_blocks_py)
    test_count_blocks_no_newline_extension = ext_functest_builder(
       _do_test_count_blocks_no_newline, _count_blocks)

    def _do_test_count_blocks_chunks(self, count_blocks):
        blob = ShaFile.from_raw_chunks(Blob.type_num, ['a\nb', '\na\n'])
        self.assertEqual({hash('a\n'): 4, hash('b\n'): 2}, _count_blocks(blob))

    test_count_blocks_chunks = functest_builder(_do_test_count_blocks_chunks,
                                                _count_blocks_py)
    test_count_blocks_chunks_extension = ext_functest_builder(
      _do_test_count_blocks_chunks, _count_blocks)

    def _do_test_count_blocks_long_lines(self, count_blocks):
        a = 'a' * 64
        data = a + 'xxx\ny\n' + a + 'zzz\n'
        blob = make_object(Blob, data=data)
        self.assertEqual({hash('a' * 64): 128, hash('xxx\n'): 4, hash('y\n'): 2,
                          hash('zzz\n'): 4},
                         _count_blocks(blob))

    test_count_blocks_long_lines = functest_builder(
      _do_test_count_blocks_long_lines, _count_blocks_py)
    test_count_blocks_long_lines_extension = ext_functest_builder(
      _do_test_count_blocks_long_lines, _count_blocks)

    def assertSimilar(self, expected_score, blob1, blob2):
        self.assertEqual(expected_score, _similarity_score(blob1, blob2))
        self.assertEqual(expected_score, _similarity_score(blob2, blob1))

    def test_similarity_score(self):
        blob0 = make_object(Blob, data='')
        blob1 = make_object(Blob, data='ab\ncd\ncd\n')
        blob2 = make_object(Blob, data='ab\n')
        blob3 = make_object(Blob, data='cd\n')
        blob4 = make_object(Blob, data='cd\ncd\n')

        self.assertSimilar(100, blob0, blob0)
        self.assertSimilar(0, blob0, blob1)
        self.assertSimilar(33, blob1, blob2)
        self.assertSimilar(33, blob1, blob3)
        self.assertSimilar(66, blob1, blob4)
        self.assertSimilar(0, blob2, blob3)
        self.assertSimilar(50, blob3, blob4)

    def test_similarity_score_cache(self):
        blob1 = make_object(Blob, data='ab\ncd\n')
        blob2 = make_object(Blob, data='ab\n')

        block_cache = {}
        self.assertEqual(
          50, _similarity_score(blob1, blob2, block_cache=block_cache))
        self.assertEqual(set([blob1.id, blob2.id]), set(block_cache))

        def fail_chunks():
            self.fail('Unexpected call to as_raw_chunks()')

        blob1.as_raw_chunks = blob2.as_raw_chunks = fail_chunks
        blob1.raw_length = lambda: 6
        blob2.raw_length = lambda: 3
        self.assertEqual(
          50, _similarity_score(blob1, blob2, block_cache=block_cache))

    def test_tree_entry_sort(self):
        sha = 'abcd' * 10
        expected_entries = [
          TreeChange.add(TreeEntry('aaa', F, sha)),
          TreeChange(CHANGE_COPY, TreeEntry('bbb', F, sha),
                     TreeEntry('aab', F, sha)),
          TreeChange(CHANGE_MODIFY, TreeEntry('bbb', F, sha),
                     TreeEntry('bbb', F, 'dabc' * 10)),
          TreeChange(CHANGE_RENAME, TreeEntry('bbc', F, sha),
                     TreeEntry('ddd', F, sha)),
          TreeChange.delete(TreeEntry('ccc', F, sha)),
          ]

        for perm in permutations(expected_entries):
            self.assertEqual(expected_entries,
                             sorted(perm, key=_tree_change_key))

    def detect_renames(self, tree1, tree2, want_unchanged=False, **kwargs):
        detector = RenameDetector(self.store, **kwargs)
        return detector.changes_with_renames(tree1.id, tree2.id,
                                             want_unchanged=want_unchanged)

    def test_no_renames(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob2 = make_object(Blob, data='a\nb\ne\nf\n')
        blob3 = make_object(Blob, data='a\nb\ng\nh\n')
        tree1 = self.commit_tree([('a', blob1), ('b', blob2)])
        tree2 = self.commit_tree([('a', blob1), ('b', blob3)])
        self.assertEqual(
          [TreeChange(CHANGE_MODIFY, ('b', F, blob2.id), ('b', F, blob3.id))],
          self.detect_renames(tree1, tree2))

    def test_exact_rename_one_to_one(self):
        blob1 = make_object(Blob, data='1')
        blob2 = make_object(Blob, data='2')
        tree1 = self.commit_tree([('a', blob1), ('b', blob2)])
        tree2 = self.commit_tree([('c', blob1), ('d', blob2)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('c', F, blob1.id)),
           TreeChange(CHANGE_RENAME, ('b', F, blob2.id), ('d', F, blob2.id))],
          self.detect_renames(tree1, tree2))

    def test_exact_rename_split_different_type(self):
        blob = make_object(Blob, data='/foo')
        tree1 = self.commit_tree([('a', blob, 0100644)])
        tree2 = self.commit_tree([('a', blob, 0120000)])
        self.assertEqual(
          [TreeChange.add(('a', 0120000, blob.id)),
           TreeChange.delete(('a', 0100644, blob.id))],
          self.detect_renames(tree1, tree2))

    def test_exact_rename_and_different_type(self):
        blob1 = make_object(Blob, data='1')
        blob2 = make_object(Blob, data='2')
        tree1 = self.commit_tree([('a', blob1)])
        tree2 = self.commit_tree([('a', blob2, 0120000), ('b', blob1)])
        self.assertEqual(
          [TreeChange.add(('a', 0120000, blob2.id)),
           TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('b', F, blob1.id))],
          self.detect_renames(tree1, tree2))

    def test_exact_rename_one_to_many(self):
        blob = make_object(Blob, data='1')
        tree1 = self.commit_tree([('a', blob)])
        tree2 = self.commit_tree([('b', blob), ('c', blob)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob.id), ('b', F, blob.id)),
           TreeChange(CHANGE_COPY, ('a', F, blob.id), ('c', F, blob.id))],
          self.detect_renames(tree1, tree2))

    def test_exact_rename_many_to_one(self):
        blob = make_object(Blob, data='1')
        tree1 = self.commit_tree([('a', blob), ('b', blob)])
        tree2 = self.commit_tree([('c', blob)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob.id), ('c', F, blob.id)),
           TreeChange.delete(('b', F, blob.id))],
          self.detect_renames(tree1, tree2))

    def test_exact_rename_many_to_many(self):
        blob = make_object(Blob, data='1')
        tree1 = self.commit_tree([('a', blob), ('b', blob)])
        tree2 = self.commit_tree([('c', blob), ('d', blob), ('e', blob)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob.id), ('c', F, blob.id)),
           TreeChange(CHANGE_COPY, ('a', F, blob.id), ('e', F, blob.id)),
           TreeChange(CHANGE_RENAME, ('b', F, blob.id), ('d', F, blob.id))],
          self.detect_renames(tree1, tree2))

    def test_exact_copy_modify(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob2 = make_object(Blob, data='a\nb\nc\ne\n')
        tree1 = self.commit_tree([('a', blob1)])
        tree2 = self.commit_tree([('a', blob2), ('b', blob1)])
        self.assertEqual(
          [TreeChange(CHANGE_MODIFY, ('a', F, blob1.id), ('a', F, blob2.id)),
           TreeChange(CHANGE_COPY, ('a', F, blob1.id), ('b', F, blob1.id))],
          self.detect_renames(tree1, tree2))

    def test_exact_copy_change_mode(self):
        blob = make_object(Blob, data='a\nb\nc\nd\n')
        tree1 = self.commit_tree([('a', blob)])
        tree2 = self.commit_tree([('a', blob, 0100755), ('b', blob)])
        self.assertEqual(
          [TreeChange(CHANGE_MODIFY, ('a', F, blob.id),
                      ('a', 0100755, blob.id)),
           TreeChange(CHANGE_COPY, ('a', F, blob.id), ('b', F, blob.id))],
          self.detect_renames(tree1, tree2))

    def test_rename_threshold(self):
        blob1 = make_object(Blob, data='a\nb\nc\n')
        blob2 = make_object(Blob, data='a\nb\nd\n')
        tree1 = self.commit_tree([('a', blob1)])
        tree2 = self.commit_tree([('b', blob2)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('b', F, blob2.id))],
          self.detect_renames(tree1, tree2, rename_threshold=50))
        self.assertEqual(
          [TreeChange.delete(('a', F, blob1.id)),
           TreeChange.add(('b', F, blob2.id))],
          self.detect_renames(tree1, tree2, rename_threshold=75))

    def test_content_rename_max_files(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd')
        blob4 = make_object(Blob, data='a\nb\nc\ne\n')
        blob2 = make_object(Blob, data='e\nf\ng\nh\n')
        blob3 = make_object(Blob, data='e\nf\ng\ni\n')
        tree1 = self.commit_tree([('a', blob1), ('b', blob2)])
        tree2 = self.commit_tree([('c', blob3), ('d', blob4)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('d', F, blob4.id)),
           TreeChange(CHANGE_RENAME, ('b', F, blob2.id), ('c', F, blob3.id))],
          self.detect_renames(tree1, tree2))
        self.assertEqual(
          [TreeChange.delete(('a', F, blob1.id)),
           TreeChange.delete(('b', F, blob2.id)),
           TreeChange.add(('c', F, blob3.id)),
           TreeChange.add(('d', F, blob4.id))],
          self.detect_renames(tree1, tree2, max_files=1))

    def test_content_rename_one_to_one(self):
        b11 = make_object(Blob, data='a\nb\nc\nd\n')
        b12 = make_object(Blob, data='a\nb\nc\ne\n')
        b21 = make_object(Blob, data='e\nf\ng\n\h')
        b22 = make_object(Blob, data='e\nf\ng\n\i')
        tree1 = self.commit_tree([('a', b11), ('b', b21)])
        tree2 = self.commit_tree([('c', b12), ('d', b22)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, b11.id), ('c', F, b12.id)),
           TreeChange(CHANGE_RENAME, ('b', F, b21.id), ('d', F, b22.id))],
          self.detect_renames(tree1, tree2))

    def test_content_rename_one_to_one_ordering(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\ne\nf\n')
        blob2 = make_object(Blob, data='a\nb\nc\nd\ng\nh\n')
        # 6/10 match to blob1, 8/10 match to blob2
        blob3 = make_object(Blob, data='a\nb\nc\nd\ng\ni\n')
        tree1 = self.commit_tree([('a', blob1), ('b', blob2)])
        tree2 = self.commit_tree([('c', blob3)])
        self.assertEqual(
          [TreeChange.delete(('a', F, blob1.id)),
           TreeChange(CHANGE_RENAME, ('b', F, blob2.id), ('c', F, blob3.id))],
          self.detect_renames(tree1, tree2))

        tree3 = self.commit_tree([('a', blob2), ('b', blob1)])
        tree4 = self.commit_tree([('c', blob3)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob2.id), ('c', F, blob3.id)),
           TreeChange.delete(('b', F, blob1.id))],
          self.detect_renames(tree3, tree4))

    def test_content_rename_one_to_many(self):
        blob1 = make_object(Blob, data='aa\nb\nc\nd\ne\n')
        blob2 = make_object(Blob, data='ab\nb\nc\nd\ne\n')  # 8/11 match
        blob3 = make_object(Blob, data='aa\nb\nc\nd\nf\n')  # 9/11 match
        tree1 = self.commit_tree([('a', blob1)])
        tree2 = self.commit_tree([('b', blob2), ('c', blob3)])
        self.assertEqual(
          [TreeChange(CHANGE_COPY, ('a', F, blob1.id), ('b', F, blob2.id)),
           TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('c', F, blob3.id))],
          self.detect_renames(tree1, tree2))

    def test_content_rename_many_to_one(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob2 = make_object(Blob, data='a\nb\nc\ne\n')
        blob3 = make_object(Blob, data='a\nb\nc\nf\n')
        tree1 = self.commit_tree([('a', blob1), ('b', blob2)])
        tree2 = self.commit_tree([('c', blob3)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('c', F, blob3.id)),
           TreeChange.delete(('b', F, blob2.id))],
          self.detect_renames(tree1, tree2))

    def test_content_rename_many_to_many(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob2 = make_object(Blob, data='a\nb\nc\ne\n')
        blob3 = make_object(Blob, data='a\nb\nc\nf\n')
        blob4 = make_object(Blob, data='a\nb\nc\ng\n')
        tree1 = self.commit_tree([('a', blob1), ('b', blob2)])
        tree2 = self.commit_tree([('c', blob3), ('d', blob4)])
        # TODO(dborowitz): Distribute renames rather than greedily choosing
        # copies.
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('c', F, blob3.id)),
           TreeChange(CHANGE_COPY, ('a', F, blob1.id), ('d', F, blob4.id)),
           TreeChange.delete(('b', F, blob2.id))],
          self.detect_renames(tree1, tree2))

    def test_content_rename_gitlink(self):
        blob1 = make_object(Blob, data='blob1')
        blob2 = make_object(Blob, data='blob2')
        link1 = '1' * 40
        link2 = '2' * 40
        tree1 = self.commit_tree([('a', blob1), ('b', link1, 0160000)])
        tree2 = self.commit_tree([('c', blob2), ('d', link2, 0160000)])
        self.assertEqual(
          [TreeChange.delete(('a', 0100644, blob1.id)),
           TreeChange.delete(('b', 0160000, link1)),
           TreeChange.add(('c', 0100644, blob2.id)),
           TreeChange.add(('d', 0160000, link2))],
          self.detect_renames(tree1, tree2))

    def test_exact_rename_swap(self):
        blob1 = make_object(Blob, data='1')
        blob2 = make_object(Blob, data='2')
        tree1 = self.commit_tree([('a', blob1), ('b', blob2)])
        tree2 = self.commit_tree([('a', blob2), ('b', blob1)])
        self.assertEqual(
          [TreeChange(CHANGE_MODIFY, ('a', F, blob1.id), ('a', F, blob2.id)),
           TreeChange(CHANGE_MODIFY, ('b', F, blob2.id), ('b', F, blob1.id))],
          self.detect_renames(tree1, tree2))
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('b', F, blob1.id)),
           TreeChange(CHANGE_RENAME, ('b', F, blob2.id), ('a', F, blob2.id))],
          self.detect_renames(tree1, tree2, rewrite_threshold=50))

    def test_content_rename_swap(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob2 = make_object(Blob, data='e\nf\ng\nh\n')
        blob3 = make_object(Blob, data='a\nb\nc\ne\n')
        blob4 = make_object(Blob, data='e\nf\ng\ni\n')
        tree1 = self.commit_tree([('a', blob1), ('b', blob2)])
        tree2 = self.commit_tree([('a', blob4), ('b', blob3)])
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('b', F, blob3.id)),
           TreeChange(CHANGE_RENAME, ('b', F, blob2.id), ('a', F, blob4.id))],
          self.detect_renames(tree1, tree2, rewrite_threshold=60))

    def test_rewrite_threshold(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob2 = make_object(Blob, data='a\nb\nc\ne\n')
        blob3 = make_object(Blob, data='a\nb\nf\ng\n')

        tree1 = self.commit_tree([('a', blob1)])
        tree2 = self.commit_tree([('a', blob3), ('b', blob2)])

        no_renames = [
          TreeChange(CHANGE_MODIFY, ('a', F, blob1.id), ('a', F, blob3.id)),
          TreeChange(CHANGE_COPY, ('a', F, blob1.id), ('b', F, blob2.id))]
        self.assertEqual(
          no_renames, self.detect_renames(tree1, tree2))
        self.assertEqual(
          no_renames, self.detect_renames(tree1, tree2, rewrite_threshold=40))
        self.assertEqual(
          [TreeChange.add(('a', F, blob3.id)),
           TreeChange(CHANGE_RENAME, ('a', F, blob1.id), ('b', F, blob2.id))],
          self.detect_renames(tree1, tree2, rewrite_threshold=80))

    def test_find_copies_harder_exact(self):
        blob = make_object(Blob, data='blob')
        tree1 = self.commit_tree([('a', blob)])
        tree2 = self.commit_tree([('a', blob), ('b', blob)])
        self.assertEqual([TreeChange.add(('b', F, blob.id))],
                         self.detect_renames(tree1, tree2))
        self.assertEqual(
          [TreeChange(CHANGE_COPY, ('a', F, blob.id), ('b', F, blob.id))],
          self.detect_renames(tree1, tree2, find_copies_harder=True))

    def test_find_copies_harder_content(self):
        blob1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob2 = make_object(Blob, data='a\nb\nc\ne\n')
        tree1 = self.commit_tree([('a', blob1)])
        tree2 = self.commit_tree([('a', blob1), ('b', blob2)])
        self.assertEqual([TreeChange.add(('b', F, blob2.id))],
                         self.detect_renames(tree1, tree2))
        self.assertEqual(
          [TreeChange(CHANGE_COPY, ('a', F, blob1.id), ('b', F, blob2.id))],
          self.detect_renames(tree1, tree2, find_copies_harder=True))

    def test_find_copies_harder_with_rewrites(self):
        blob_a1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob_a2 = make_object(Blob, data='f\ng\nh\ni\n')
        blob_b2 = make_object(Blob, data='a\nb\nc\ne\n')
        tree1 = self.commit_tree([('a', blob_a1)])
        tree2 = self.commit_tree([('a', blob_a2), ('b', blob_b2)])
        self.assertEqual(
          [TreeChange(CHANGE_MODIFY, ('a', F, blob_a1.id),
                      ('a', F, blob_a2.id)),
           TreeChange(CHANGE_COPY, ('a', F, blob_a1.id), ('b', F, blob_b2.id))],
          self.detect_renames(tree1, tree2, find_copies_harder=True))
        self.assertEqual(
          [TreeChange.add(('a', F, blob_a2.id)),
           TreeChange(CHANGE_RENAME, ('a', F, blob_a1.id),
                      ('b', F, blob_b2.id))],
          self.detect_renames(tree1, tree2, rewrite_threshold=50,
                              find_copies_harder=True))

    def test_reuse_detector(self):
        blob = make_object(Blob, data='blob')
        tree1 = self.commit_tree([('a', blob)])
        tree2 = self.commit_tree([('b', blob)])
        detector = RenameDetector(self.store)
        changes = [TreeChange(CHANGE_RENAME, ('a', F, blob.id),
                              ('b', F, blob.id))]
        self.assertEqual(changes,
                         detector.changes_with_renames(tree1.id, tree2.id))
        self.assertEqual(changes,
                         detector.changes_with_renames(tree1.id, tree2.id))

    def test_want_unchanged(self):
        blob_a1 = make_object(Blob, data='a\nb\nc\nd\n')
        blob_b = make_object(Blob, data='b')
        blob_c2 = make_object(Blob, data='a\nb\nc\ne\n')
        tree1 = self.commit_tree([('a', blob_a1), ('b', blob_b)])
        tree2 = self.commit_tree([('c', blob_c2), ('b', blob_b)])
        detector = RenameDetector(self.store)
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob_a1.id),
                      ('c', F, blob_c2.id))],
          self.detect_renames(tree1, tree2))
        self.assertEqual(
          [TreeChange(CHANGE_RENAME, ('a', F, blob_a1.id),
                      ('c', F, blob_c2.id)),
           TreeChange(CHANGE_UNCHANGED, ('b', F, blob_b.id),
                      ('b', F, blob_b.id))],
          self.detect_renames(tree1, tree2, want_unchanged=True))

########NEW FILE########
__FILENAME__ = test_fastexport
# test_fastexport.py -- Fast export/import functionality
# Copyright (C) 2010 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

from cStringIO import StringIO
import stat

from dulwich.object_store import (
    MemoryObjectStore,
    )
from dulwich.objects import (
    Blob,
    Commit,
    Tree,
    )
from dulwich.repo import (
    MemoryRepo,
    )
from dulwich.tests import (
    SkipTest,
    TestCase,
    )


class GitFastExporterTests(TestCase):
    """Tests for the GitFastExporter tests."""

    def setUp(self):
        super(GitFastExporterTests, self).setUp()
        self.store = MemoryObjectStore()
        self.stream = StringIO()
        try:
            from dulwich.fastexport import GitFastExporter
        except ImportError:
            raise SkipTest("python-fastimport not available")
        self.fastexporter = GitFastExporter(self.stream, self.store)

    def test_emit_blob(self):
        b = Blob()
        b.data = "fooBAR"
        self.fastexporter.emit_blob(b)
        self.assertEqual('blob\nmark :1\ndata 6\nfooBAR\n',
            self.stream.getvalue())

    def test_emit_commit(self):
        b = Blob()
        b.data = "FOO"
        t = Tree()
        t.add("foo", stat.S_IFREG | 0644, b.id)
        c = Commit()
        c.committer = c.author = "Jelmer <jelmer@host>"
        c.author_time = c.commit_time = 1271345553
        c.author_timezone = c.commit_timezone = 0
        c.message = "msg"
        c.tree = t.id
        self.store.add_objects([(b, None), (t, None), (c, None)])
        self.fastexporter.emit_commit(c, "refs/heads/master")
        self.assertEqual("""blob
mark :1
data 3
FOO
commit refs/heads/master
mark :2
author Jelmer <jelmer@host> 1271345553 +0000
committer Jelmer <jelmer@host> 1271345553 +0000
data 3
msg
M 644 1 foo
""", self.stream.getvalue())


class GitImportProcessorTests(TestCase):
    """Tests for the GitImportProcessor tests."""

    def setUp(self):
        super(GitImportProcessorTests, self).setUp()
        self.repo = MemoryRepo()
        try:
            from dulwich.fastexport import GitImportProcessor
        except ImportError:
            raise SkipTest("python-fastimport not available")
        self.processor = GitImportProcessor(self.repo)

    def test_commit_handler(self):
        from fastimport import commands
        cmd = commands.CommitCommand("refs/heads/foo", "mrkr",
            ("Jelmer", "jelmer@samba.org", 432432432.0, 3600),
            ("Jelmer", "jelmer@samba.org", 432432432.0, 3600),
            "FOO", None, [], [])
        self.processor.commit_handler(cmd)
        commit = self.repo[self.processor.last_commit]
        self.assertEqual("Jelmer <jelmer@samba.org>", commit.author)
        self.assertEqual("Jelmer <jelmer@samba.org>", commit.committer)
        self.assertEqual("FOO", commit.message)
        self.assertEqual([], commit.parents)
        self.assertEqual(432432432.0, commit.commit_time)
        self.assertEqual(432432432.0, commit.author_time)
        self.assertEqual(3600, commit.commit_timezone)
        self.assertEqual(3600, commit.author_timezone)
        self.assertEqual(commit, self.repo["refs/heads/foo"])

    def test_import_stream(self):
        markers = self.processor.import_stream(StringIO("""blob
mark :1
data 11
text for a

commit refs/heads/master
mark :2
committer Joe Foo <joe@foo.com> 1288287382 +0000
data 20
<The commit message>
M 100644 :1 a

"""))
        self.assertEqual(2, len(markers))
        self.assertTrue(isinstance(self.repo[markers["1"]], Blob))
        self.assertTrue(isinstance(self.repo[markers["2"]], Commit))

    def test_file_add(self):
        from fastimport import commands
        cmd = commands.BlobCommand("23", "data")
        self.processor.blob_handler(cmd)
        cmd = commands.CommitCommand("refs/heads/foo", "mrkr",
            ("Jelmer", "jelmer@samba.org", 432432432.0, 3600),
            ("Jelmer", "jelmer@samba.org", 432432432.0, 3600),
            "FOO", None, [], [commands.FileModifyCommand("path", 0100644, ":23", None)])
        self.processor.commit_handler(cmd)
        commit = self.repo[self.processor.last_commit]
        self.assertEqual([
            ('path', 0100644, '6320cd248dd8aeaab759d5871f8781b5c0505172')],
            self.repo[commit.tree].items())

    def simple_commit(self):
        from fastimport import commands
        cmd = commands.BlobCommand("23", "data")
        self.processor.blob_handler(cmd)
        cmd = commands.CommitCommand("refs/heads/foo", "mrkr",
            ("Jelmer", "jelmer@samba.org", 432432432.0, 3600),
            ("Jelmer", "jelmer@samba.org", 432432432.0, 3600),
            "FOO", None, [], [commands.FileModifyCommand("path", 0100644, ":23", None)])
        self.processor.commit_handler(cmd)
        commit = self.repo[self.processor.last_commit]
        return commit

    def make_file_commit(self, file_cmds):
        """Create a trivial commit with the specified file commands.

        :param file_cmds: File commands to run.
        :return: The created commit object
        """
        from fastimport import commands
        cmd = commands.CommitCommand("refs/heads/foo", "mrkr",
            ("Jelmer", "jelmer@samba.org", 432432432.0, 3600),
            ("Jelmer", "jelmer@samba.org", 432432432.0, 3600),
            "FOO", None, [], file_cmds)
        self.processor.commit_handler(cmd)
        return self.repo[self.processor.last_commit]

    def test_file_copy(self):
        from fastimport import commands
        self.simple_commit()
        commit = self.make_file_commit([commands.FileCopyCommand("path", "new_path")])
        self.assertEqual([
            ('new_path', 0100644, '6320cd248dd8aeaab759d5871f8781b5c0505172'),
            ('path', 0100644, '6320cd248dd8aeaab759d5871f8781b5c0505172'),
            ], self.repo[commit.tree].items())

    def test_file_move(self):
        from fastimport import commands
        self.simple_commit()
        commit = self.make_file_commit([commands.FileRenameCommand("path", "new_path")])
        self.assertEqual([
            ('new_path', 0100644, '6320cd248dd8aeaab759d5871f8781b5c0505172'),
            ], self.repo[commit.tree].items())

    def test_file_delete(self):
        from fastimport import commands
        self.simple_commit()
        commit = self.make_file_commit([commands.FileDeleteCommand("path")])
        self.assertEqual([], self.repo[commit.tree].items())

    def test_file_deleteall(self):
        from fastimport import commands
        self.simple_commit()
        commit = self.make_file_commit([commands.FileDeleteAllCommand()])
        self.assertEqual([], self.repo[commit.tree].items())

########NEW FILE########
__FILENAME__ = test_file
# test_file.py -- Test for git files
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

import errno
import os
import shutil
import sys
import tempfile

from dulwich.file import GitFile, fancy_rename
from dulwich.tests import (
    SkipTest,
    TestCase,
    )


class FancyRenameTests(TestCase):

    def setUp(self):
        super(FancyRenameTests, self).setUp()
        self._tempdir = tempfile.mkdtemp()
        self.foo = self.path('foo')
        self.bar = self.path('bar')
        self.create(self.foo, 'foo contents')

    def tearDown(self):
        shutil.rmtree(self._tempdir)
        super(FancyRenameTests, self).tearDown()

    def path(self, filename):
        return os.path.join(self._tempdir, filename)

    def create(self, path, contents):
        f = open(path, 'wb')
        f.write(contents)
        f.close()

    def test_no_dest_exists(self):
        self.assertFalse(os.path.exists(self.bar))
        fancy_rename(self.foo, self.bar)
        self.assertFalse(os.path.exists(self.foo))

        new_f = open(self.bar, 'rb')
        self.assertEqual('foo contents', new_f.read())
        new_f.close()
         
    def test_dest_exists(self):
        self.create(self.bar, 'bar contents')
        fancy_rename(self.foo, self.bar)
        self.assertFalse(os.path.exists(self.foo))

        new_f = open(self.bar, 'rb')
        self.assertEqual('foo contents', new_f.read())
        new_f.close()

    def test_dest_opened(self):
        if sys.platform != "win32":
            raise SkipTest("platform allows overwriting open files")
        self.create(self.bar, 'bar contents')
        dest_f = open(self.bar, 'rb')
        self.assertRaises(OSError, fancy_rename, self.foo, self.bar)
        dest_f.close()
        self.assertTrue(os.path.exists(self.path('foo')))

        new_f = open(self.foo, 'rb')
        self.assertEqual('foo contents', new_f.read())
        new_f.close()

        new_f = open(self.bar, 'rb')
        self.assertEqual('bar contents', new_f.read())
        new_f.close()


class GitFileTests(TestCase):

    def setUp(self):
        super(GitFileTests, self).setUp()
        self._tempdir = tempfile.mkdtemp()
        f = open(self.path('foo'), 'wb')
        f.write('foo contents')
        f.close()

    def tearDown(self):
        shutil.rmtree(self._tempdir)
        super(GitFileTests, self).tearDown()

    def path(self, filename):
        return os.path.join(self._tempdir, filename)

    def test_invalid(self):
        foo = self.path('foo')
        self.assertRaises(IOError, GitFile, foo, mode='r')
        self.assertRaises(IOError, GitFile, foo, mode='ab')
        self.assertRaises(IOError, GitFile, foo, mode='r+b')
        self.assertRaises(IOError, GitFile, foo, mode='w+b')
        self.assertRaises(IOError, GitFile, foo, mode='a+bU')

    def test_readonly(self):
        f = GitFile(self.path('foo'), 'rb')
        self.assertTrue(isinstance(f, file))
        self.assertEqual('foo contents', f.read())
        self.assertEqual('', f.read())
        f.seek(4)
        self.assertEqual('contents', f.read())
        f.close()

    def test_default_mode(self):
        f = GitFile(self.path('foo'))
        self.assertEqual('foo contents', f.read())
        f.close()

    def test_write(self):
        foo = self.path('foo')
        foo_lock = '%s.lock' % foo

        orig_f = open(foo, 'rb')
        self.assertEqual(orig_f.read(), 'foo contents')
        orig_f.close()

        self.assertFalse(os.path.exists(foo_lock))
        f = GitFile(foo, 'wb')
        self.assertFalse(f.closed)
        self.assertRaises(AttributeError, getattr, f, 'not_a_file_property')

        self.assertTrue(os.path.exists(foo_lock))
        f.write('new stuff')
        f.seek(4)
        f.write('contents')
        f.close()
        self.assertFalse(os.path.exists(foo_lock))

        new_f = open(foo, 'rb')
        self.assertEqual('new contents', new_f.read())
        new_f.close()

    def test_open_twice(self):
        foo = self.path('foo')
        f1 = GitFile(foo, 'wb')
        f1.write('new')
        try:
            f2 = GitFile(foo, 'wb')
            self.fail()
        except OSError, e:
            self.assertEqual(errno.EEXIST, e.errno)
        f1.write(' contents')
        f1.close()

        # Ensure trying to open twice doesn't affect original.
        f = open(foo, 'rb')
        self.assertEqual('new contents', f.read())
        f.close()

    def test_abort(self):
        foo = self.path('foo')
        foo_lock = '%s.lock' % foo

        orig_f = open(foo, 'rb')
        self.assertEqual(orig_f.read(), 'foo contents')
        orig_f.close()

        f = GitFile(foo, 'wb')
        f.write('new contents')
        f.abort()
        self.assertTrue(f.closed)
        self.assertFalse(os.path.exists(foo_lock))

        new_orig_f = open(foo, 'rb')
        self.assertEqual(new_orig_f.read(), 'foo contents')
        new_orig_f.close()

    def test_abort_close(self):
        foo = self.path('foo')
        f = GitFile(foo, 'wb')
        f.abort()
        try:
            f.close()
        except (IOError, OSError):
            self.fail()

        f = GitFile(foo, 'wb')
        f.close()
        try:
            f.abort()
        except (IOError, OSError):
            self.fail()

    def test_abort_close_removed(self):
        foo = self.path('foo')
        f = GitFile(foo, 'wb')

        f._file.close()
        os.remove(foo+".lock")

        f.abort()
        self.assertTrue(f._closed)

########NEW FILE########
__FILENAME__ = test_hooks
# test_hooks.py -- Tests for executing hooks
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for executing hooks."""

import os
import stat
import shutil
import tempfile
import warnings

from dulwich import errors

from dulwich.hooks import (
    PreCommitShellHook,
    PostCommitShellHook,
    CommitMsgShellHook,
)

from dulwich.tests import TestCase


class ShellHookTests(TestCase):

    def setUp(self):
        if os.name != 'posix':
            self.skipTest('shell hook tests requires POSIX shell')

    def test_hook_pre_commit(self):
        pre_commit_fail = """#!/bin/sh
exit 1
"""

        pre_commit_success = """#!/bin/sh
exit 0
"""

        repo_dir = os.path.join(tempfile.mkdtemp())
        os.mkdir(os.path.join(repo_dir, 'hooks'))
        self.addCleanup(shutil.rmtree, repo_dir)

        pre_commit = os.path.join(repo_dir, 'hooks', 'pre-commit')
        hook = PreCommitShellHook(repo_dir)

        f = open(pre_commit, 'wb')
        try:
            f.write(pre_commit_fail)
        finally:
            f.close()
        os.chmod(pre_commit, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        self.assertRaises(errors.HookError, hook.execute)

        f = open(pre_commit, 'wb')
        try:
            f.write(pre_commit_success)
        finally:
            f.close()
        os.chmod(pre_commit, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        hook.execute()

    def test_hook_commit_msg(self):

        commit_msg_fail = """#!/bin/sh
exit 1
"""

        commit_msg_success = """#!/bin/sh
exit 0
"""

        repo_dir = os.path.join(tempfile.mkdtemp())
        os.mkdir(os.path.join(repo_dir, 'hooks'))
        self.addCleanup(shutil.rmtree, repo_dir)

        commit_msg = os.path.join(repo_dir, 'hooks', 'commit-msg')
        hook = CommitMsgShellHook(repo_dir)

        f = open(commit_msg, 'wb')
        try:
            f.write(commit_msg_fail)
        finally:
            f.close()
        os.chmod(commit_msg, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        self.assertRaises(errors.HookError, hook.execute, 'failed commit')

        f = open(commit_msg, 'wb')
        try:
            f.write(commit_msg_success)
        finally:
            f.close()
        os.chmod(commit_msg, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        hook.execute('empty commit')

    def test_hook_post_commit(self):

        (fd, path) = tempfile.mkstemp()
        post_commit_msg = """#!/bin/sh
unlink %(file)s
""" % {'file': path}

        post_commit_msg_fail = """#!/bin/sh
exit 1
"""

        repo_dir = os.path.join(tempfile.mkdtemp())
        os.mkdir(os.path.join(repo_dir, 'hooks'))
        self.addCleanup(shutil.rmtree, repo_dir)

        post_commit = os.path.join(repo_dir, 'hooks', 'post-commit')
        hook = PostCommitShellHook(repo_dir)

        f = open(post_commit, 'wb')
        try:
            f.write(post_commit_msg_fail)
        finally:
            f.close()
        os.chmod(post_commit, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        self.assertRaises(errors.HookError, hook.execute)

        f = open(post_commit, 'wb')
        try:
            f.write(post_commit_msg)
        finally:
            f.close()
        os.chmod(post_commit, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        hook.execute()
        self.assertFalse(os.path.exists(path))

########NEW FILE########
__FILENAME__ = test_index
# test_index.py -- Tests for the git index
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for the index."""


from cStringIO import (
    StringIO,
    )
import os
import shutil
import stat
import struct
import tempfile

from dulwich.index import (
    Index,
    build_index_from_tree,
    cleanup_mode,
    commit_tree,
    index_entry_from_stat,
    read_index,
    write_cache_time,
    write_index,
    )
from dulwich.object_store import (
    MemoryObjectStore,
    )
from dulwich.objects import (
    Blob,
    Tree,
    )
from dulwich.repo import Repo
from dulwich.tests import TestCase


class IndexTestCase(TestCase):

    datadir = os.path.join(os.path.dirname(__file__), 'data/indexes')

    def get_simple_index(self, name):
        return Index(os.path.join(self.datadir, name))


class SimpleIndexTestCase(IndexTestCase):

    def test_len(self):
        self.assertEqual(1, len(self.get_simple_index("index")))

    def test_iter(self):
        self.assertEqual(['bla'], list(self.get_simple_index("index")))

    def test_getitem(self):
        self.assertEqual(((1230680220, 0), (1230680220, 0), 2050, 3761020,
                           33188, 1000, 1000, 0,
                           'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391', 0),
                          self.get_simple_index("index")["bla"])

    def test_empty(self):
        i = self.get_simple_index("notanindex")
        self.assertEqual(0, len(i))
        self.assertFalse(os.path.exists(i._filename))

    def test_against_empty_tree(self):
        i = self.get_simple_index("index")
        changes = list(i.changes_from_tree(MemoryObjectStore(), None))
        self.assertEqual(1, len(changes))
        (oldname, newname), (oldmode, newmode), (oldsha, newsha) = changes[0]
        self.assertEqual('bla', newname)
        self.assertEqual('e69de29bb2d1d6434b8b29ae775ad8c2e48c5391', newsha)

class SimpleIndexWriterTestCase(IndexTestCase):

    def setUp(self):
        IndexTestCase.setUp(self)
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        IndexTestCase.tearDown(self)
        shutil.rmtree(self.tempdir)

    def test_simple_write(self):
        entries = [('barbla', (1230680220, 0), (1230680220, 0), 2050, 3761020,
                    33188, 1000, 1000, 0,
                    'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391', 0)]
        filename = os.path.join(self.tempdir, 'test-simple-write-index')
        x = open(filename, 'w+')
        try:
            write_index(x, entries)
        finally:
            x.close()
        x = open(filename, 'r')
        try:
            self.assertEqual(entries, list(read_index(x)))
        finally:
            x.close()


class CommitTreeTests(TestCase):

    def setUp(self):
        super(CommitTreeTests, self).setUp()
        self.store = MemoryObjectStore()

    def test_single_blob(self):
        blob = Blob()
        blob.data = "foo"
        self.store.add_object(blob)
        blobs = [("bla", blob.id, stat.S_IFREG)]
        rootid = commit_tree(self.store, blobs)
        self.assertEqual(rootid, "1a1e80437220f9312e855c37ac4398b68e5c1d50")
        self.assertEqual((stat.S_IFREG, blob.id), self.store[rootid]["bla"])
        self.assertEqual(set([rootid, blob.id]), set(self.store._data.keys()))

    def test_nested(self):
        blob = Blob()
        blob.data = "foo"
        self.store.add_object(blob)
        blobs = [("bla/bar", blob.id, stat.S_IFREG)]
        rootid = commit_tree(self.store, blobs)
        self.assertEqual(rootid, "d92b959b216ad0d044671981196781b3258fa537")
        dirid = self.store[rootid]["bla"][1]
        self.assertEqual(dirid, "c1a1deb9788150829579a8b4efa6311e7b638650")
        self.assertEqual((stat.S_IFDIR, dirid), self.store[rootid]["bla"])
        self.assertEqual((stat.S_IFREG, blob.id), self.store[dirid]["bar"])
        self.assertEqual(set([rootid, dirid, blob.id]),
                          set(self.store._data.keys()))


class CleanupModeTests(TestCase):

    def test_file(self):
        self.assertEqual(0100644, cleanup_mode(0100000))

    def test_executable(self):
        self.assertEqual(0100755, cleanup_mode(0100711))

    def test_symlink(self):
        self.assertEqual(0120000, cleanup_mode(0120711))

    def test_dir(self):
        self.assertEqual(0040000, cleanup_mode(040531))

    def test_submodule(self):
        self.assertEqual(0160000, cleanup_mode(0160744))


class WriteCacheTimeTests(TestCase):

    def test_write_string(self):
        f = StringIO()
        self.assertRaises(TypeError, write_cache_time, f, "foo")

    def test_write_int(self):
        f = StringIO()
        write_cache_time(f, 434343)
        self.assertEqual(struct.pack(">LL", 434343, 0), f.getvalue())

    def test_write_tuple(self):
        f = StringIO()
        write_cache_time(f, (434343, 21))
        self.assertEqual(struct.pack(">LL", 434343, 21), f.getvalue())

    def test_write_float(self):
        f = StringIO()
        write_cache_time(f, 434343.000000021)
        self.assertEqual(struct.pack(">LL", 434343, 21), f.getvalue())


class IndexEntryFromStatTests(TestCase):

    def test_simple(self):
        st = os.stat_result((16877, 131078, 64769L,
                154, 1000, 1000, 12288,
                1323629595, 1324180496, 1324180496))
        entry = index_entry_from_stat(st, "22" * 20, 0)
        self.assertEqual(entry, (
            1324180496,
            1324180496,
            64769L,
            131078,
            16384,
            1000,
            1000,
            12288,
            '2222222222222222222222222222222222222222',
            0))

    def test_override_mode(self):
        st = os.stat_result((stat.S_IFREG + 0644, 131078, 64769L,
                154, 1000, 1000, 12288,
                1323629595, 1324180496, 1324180496))
        entry = index_entry_from_stat(st, "22" * 20, 0,
                mode=stat.S_IFREG + 0755)
        self.assertEqual(entry, (
            1324180496,
            1324180496,
            64769L,
            131078,
            33261,
            1000,
            1000,
            12288,
            '2222222222222222222222222222222222222222',
            0))


class BuildIndexTests(TestCase):

    def assertReasonableIndexEntry(self, index_entry, mode, filesize, sha):
        self.assertEquals(index_entry[4], mode)  # mode
        self.assertEquals(index_entry[7], filesize)  # filesize
        self.assertEquals(index_entry[8], sha)  # sha

    def assertFileContents(self, path, contents, symlink=False):
        if symlink:
            self.assertEquals(os.readlink(path), contents)
        else:
            f = open(path, 'rb')
            try:
                self.assertEquals(f.read(), contents)
            finally:
                f.close()

    def test_empty(self):
        repo_dir = tempfile.mkdtemp()
        repo = Repo.init(repo_dir)
        self.addCleanup(shutil.rmtree, repo_dir)

        tree = Tree()
        repo.object_store.add_object(tree)

        build_index_from_tree(repo.path, repo.index_path(),
                repo.object_store, tree.id)

        # Verify index entries
        index = repo.open_index()
        self.assertEquals(len(index), 0)

        # Verify no files
        self.assertEquals(['.git'], os.listdir(repo.path))

    def test_nonempty(self):
        if os.name != 'posix':
            self.skipTest("test depends on POSIX shell")

        repo_dir = tempfile.mkdtemp()
        repo = Repo.init(repo_dir)
        self.addCleanup(shutil.rmtree, repo_dir)

        # Populate repo
        filea = Blob.from_string('file a')
        fileb = Blob.from_string('file b')
        filed = Blob.from_string('file d')
        filee = Blob.from_string('d')

        tree = Tree()
        tree['a'] = (stat.S_IFREG | 0644, filea.id)
        tree['b'] = (stat.S_IFREG | 0644, fileb.id)
        tree['c/d'] = (stat.S_IFREG | 0644, filed.id)
        tree['c/e'] = (stat.S_IFLNK, filee.id)  # symlink

        repo.object_store.add_objects([(o, None)
            for o in [filea, fileb, filed, filee, tree]])

        build_index_from_tree(repo.path, repo.index_path(),
                repo.object_store, tree.id)

        # Verify index entries
        index = repo.open_index()
        self.assertEquals(len(index), 4)

        # filea
        apath = os.path.join(repo.path, 'a')
        self.assertTrue(os.path.exists(apath))
        self.assertReasonableIndexEntry(index['a'],
            stat.S_IFREG | 0644, 6, filea.id)
        self.assertFileContents(apath, 'file a')

        # fileb
        bpath = os.path.join(repo.path, 'b')
        self.assertTrue(os.path.exists(bpath))
        self.assertReasonableIndexEntry(index['b'],
            stat.S_IFREG | 0644, 6, fileb.id)
        self.assertFileContents(bpath, 'file b')

        # filed
        dpath = os.path.join(repo.path, 'c', 'd')
        self.assertTrue(os.path.exists(dpath))
        self.assertReasonableIndexEntry(index['c/d'], 
            stat.S_IFREG | 0644, 6, filed.id)
        self.assertFileContents(dpath, 'file d')

        # symlink to d
        epath = os.path.join(repo.path, 'c', 'e')
        self.assertTrue(os.path.exists(epath))
        self.assertReasonableIndexEntry(index['c/e'], 
            stat.S_IFLNK, 1, filee.id)
        self.assertFileContents(epath, 'd', symlink=True)

        # Verify no extra files
        self.assertEquals(['.git', 'a', 'b', 'c'],
            sorted(os.listdir(repo.path)))
        self.assertEquals(['d', 'e'], 
            sorted(os.listdir(os.path.join(repo.path, 'c'))))

########NEW FILE########
__FILENAME__ = test_lru_cache
# Copyright (C) 2006, 2008 Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""Tests for the lru_cache module."""

from dulwich import (
    lru_cache,
    )
from dulwich.tests import (
    TestCase,
    )


class TestLRUCache(TestCase):
    """Test that LRU cache properly keeps track of entries."""

    def test_cache_size(self):
        cache = lru_cache.LRUCache(max_cache=10)
        self.assertEqual(10, cache.cache_size())

        cache = lru_cache.LRUCache(max_cache=256)
        self.assertEqual(256, cache.cache_size())

        cache.resize(512)
        self.assertEqual(512, cache.cache_size())

    def test_missing(self):
        cache = lru_cache.LRUCache(max_cache=10)

        self.failIf('foo' in cache)
        self.assertRaises(KeyError, cache.__getitem__, 'foo')

        cache['foo'] = 'bar'
        self.assertEqual('bar', cache['foo'])
        self.failUnless('foo' in cache)
        self.failIf('bar' in cache)

    def test_map_None(self):
        # Make sure that we can properly map None as a key.
        cache = lru_cache.LRUCache(max_cache=10)
        self.failIf(None in cache)
        cache[None] = 1
        self.assertEqual(1, cache[None])
        cache[None] = 2
        self.assertEqual(2, cache[None])
        # Test the various code paths of __getitem__, to make sure that we can
        # handle when None is the key for the LRU and the MRU
        cache[1] = 3
        cache[None] = 1
        cache[None]
        cache[1]
        cache[None]
        self.assertEqual([None, 1], [n.key for n in cache._walk_lru()])

    def test_add__null_key(self):
        cache = lru_cache.LRUCache(max_cache=10)
        self.assertRaises(ValueError, cache.add, lru_cache._null_key, 1)

    def test_overflow(self):
        """Adding extra entries will pop out old ones."""
        cache = lru_cache.LRUCache(max_cache=1, after_cleanup_count=1)

        cache['foo'] = 'bar'
        # With a max cache of 1, adding 'baz' should pop out 'foo'
        cache['baz'] = 'biz'

        self.failIf('foo' in cache)
        self.failUnless('baz' in cache)

        self.assertEqual('biz', cache['baz'])

    def test_by_usage(self):
        """Accessing entries bumps them up in priority."""
        cache = lru_cache.LRUCache(max_cache=2)

        cache['baz'] = 'biz'
        cache['foo'] = 'bar'

        self.assertEqual('biz', cache['baz'])

        # This must kick out 'foo' because it was the last accessed
        cache['nub'] = 'in'

        self.failIf('foo' in cache)

    def test_cleanup(self):
        """Test that we can use a cleanup function."""
        cleanup_called = []
        def cleanup_func(key, val):
            cleanup_called.append((key, val))

        cache = lru_cache.LRUCache(max_cache=2)

        cache.add('baz', '1', cleanup=cleanup_func)
        cache.add('foo', '2', cleanup=cleanup_func)
        cache.add('biz', '3', cleanup=cleanup_func)

        self.assertEqual([('baz', '1')], cleanup_called)

        # 'foo' is now most recent, so final cleanup will call it last
        cache['foo']
        cache.clear()
        self.assertEqual([('baz', '1'), ('biz', '3'), ('foo', '2')],
                         cleanup_called)

    def test_cleanup_on_replace(self):
        """Replacing an object should cleanup the old value."""
        cleanup_called = []
        def cleanup_func(key, val):
            cleanup_called.append((key, val))

        cache = lru_cache.LRUCache(max_cache=2)
        cache.add(1, 10, cleanup=cleanup_func)
        cache.add(2, 20, cleanup=cleanup_func)
        cache.add(2, 25, cleanup=cleanup_func)

        self.assertEqual([(2, 20)], cleanup_called)
        self.assertEqual(25, cache[2])

        # Even __setitem__ should make sure cleanup() is called
        cache[2] = 26
        self.assertEqual([(2, 20), (2, 25)], cleanup_called)

    def test_len(self):
        cache = lru_cache.LRUCache(max_cache=10, after_cleanup_count=10)

        cache[1] = 10
        cache[2] = 20
        cache[3] = 30
        cache[4] = 40

        self.assertEqual(4, len(cache))

        cache[5] = 50
        cache[6] = 60
        cache[7] = 70
        cache[8] = 80

        self.assertEqual(8, len(cache))

        cache[1] = 15 # replacement

        self.assertEqual(8, len(cache))

        cache[9] = 90
        cache[10] = 100
        cache[11] = 110

        # We hit the max
        self.assertEqual(10, len(cache))
        self.assertEqual([11, 10, 9, 1, 8, 7, 6, 5, 4, 3],
                         [n.key for n in cache._walk_lru()])

    def test_cleanup_shrinks_to_after_clean_count(self):
        cache = lru_cache.LRUCache(max_cache=5, after_cleanup_count=3)

        cache.add(1, 10)
        cache.add(2, 20)
        cache.add(3, 25)
        cache.add(4, 30)
        cache.add(5, 35)

        self.assertEqual(5, len(cache))
        # This will bump us over the max, which causes us to shrink down to
        # after_cleanup_cache size
        cache.add(6, 40)
        self.assertEqual(3, len(cache))

    def test_after_cleanup_larger_than_max(self):
        cache = lru_cache.LRUCache(max_cache=5, after_cleanup_count=10)
        self.assertEqual(5, cache._after_cleanup_count)

    def test_after_cleanup_none(self):
        cache = lru_cache.LRUCache(max_cache=5, after_cleanup_count=None)
        # By default _after_cleanup_size is 80% of the normal size
        self.assertEqual(4, cache._after_cleanup_count)

    def test_cleanup(self):
        cache = lru_cache.LRUCache(max_cache=5, after_cleanup_count=2)

        # Add these in order
        cache.add(1, 10)
        cache.add(2, 20)
        cache.add(3, 25)
        cache.add(4, 30)
        cache.add(5, 35)

        self.assertEqual(5, len(cache))
        # Force a compaction
        cache.cleanup()
        self.assertEqual(2, len(cache))

    def test_preserve_last_access_order(self):
        cache = lru_cache.LRUCache(max_cache=5)

        # Add these in order
        cache.add(1, 10)
        cache.add(2, 20)
        cache.add(3, 25)
        cache.add(4, 30)
        cache.add(5, 35)

        self.assertEqual([5, 4, 3, 2, 1], [n.key for n in cache._walk_lru()])

        # Now access some randomly
        cache[2]
        cache[5]
        cache[3]
        cache[2]
        self.assertEqual([2, 3, 5, 4, 1], [n.key for n in cache._walk_lru()])

    def test_get(self):
        cache = lru_cache.LRUCache(max_cache=5)

        cache.add(1, 10)
        cache.add(2, 20)
        self.assertEqual(20, cache.get(2))
        self.assertEqual(None, cache.get(3))
        obj = object()
        self.assertTrue(obj is cache.get(3, obj))
        self.assertEqual([2, 1], [n.key for n in cache._walk_lru()])
        self.assertEqual(10, cache.get(1))
        self.assertEqual([1, 2], [n.key for n in cache._walk_lru()])

    def test_keys(self):
        cache = lru_cache.LRUCache(max_cache=5, after_cleanup_count=5)

        cache[1] = 2
        cache[2] = 3
        cache[3] = 4
        self.assertEqual([1, 2, 3], sorted(cache.keys()))
        cache[4] = 5
        cache[5] = 6
        cache[6] = 7
        self.assertEqual([2, 3, 4, 5, 6], sorted(cache.keys()))

    def test_resize_smaller(self):
        cache = lru_cache.LRUCache(max_cache=5, after_cleanup_count=4)
        cache[1] = 2
        cache[2] = 3
        cache[3] = 4
        cache[4] = 5
        cache[5] = 6
        self.assertEqual([1, 2, 3, 4, 5], sorted(cache.keys()))
        cache[6] = 7
        self.assertEqual([3, 4, 5, 6], sorted(cache.keys()))
        # Now resize to something smaller, which triggers a cleanup
        cache.resize(max_cache=3, after_cleanup_count=2)
        self.assertEqual([5, 6], sorted(cache.keys()))
        # Adding something will use the new size
        cache[7] = 8
        self.assertEqual([5, 6, 7], sorted(cache.keys()))
        cache[8] = 9
        self.assertEqual([7, 8], sorted(cache.keys()))

    def test_resize_larger(self):
        cache = lru_cache.LRUCache(max_cache=5, after_cleanup_count=4)
        cache[1] = 2
        cache[2] = 3
        cache[3] = 4
        cache[4] = 5
        cache[5] = 6
        self.assertEqual([1, 2, 3, 4, 5], sorted(cache.keys()))
        cache[6] = 7
        self.assertEqual([3, 4, 5, 6], sorted(cache.keys()))
        cache.resize(max_cache=8, after_cleanup_count=6)
        self.assertEqual([3, 4, 5, 6], sorted(cache.keys()))
        cache[7] = 8
        cache[8] = 9
        cache[9] = 10
        cache[10] = 11
        self.assertEqual([3, 4, 5, 6, 7, 8, 9, 10], sorted(cache.keys()))
        cache[11] = 12 # triggers cleanup back to new after_cleanup_count
        self.assertEqual([6, 7, 8, 9, 10, 11], sorted(cache.keys()))


class TestLRUSizeCache(TestCase):

    def test_basic_init(self):
        cache = lru_cache.LRUSizeCache()
        self.assertEqual(2048, cache._max_cache)
        self.assertEqual(int(cache._max_size*0.8), cache._after_cleanup_size)
        self.assertEqual(0, cache._value_size)

    def test_add__null_key(self):
        cache = lru_cache.LRUSizeCache()
        self.assertRaises(ValueError, cache.add, lru_cache._null_key, 1)

    def test_add_tracks_size(self):
        cache = lru_cache.LRUSizeCache()
        self.assertEqual(0, cache._value_size)
        cache.add('my key', 'my value text')
        self.assertEqual(13, cache._value_size)

    def test_remove_tracks_size(self):
        cache = lru_cache.LRUSizeCache()
        self.assertEqual(0, cache._value_size)
        cache.add('my key', 'my value text')
        self.assertEqual(13, cache._value_size)
        node = cache._cache['my key']
        cache._remove_node(node)
        self.assertEqual(0, cache._value_size)

    def test_no_add_over_size(self):
        """Adding a large value may not be cached at all."""
        cache = lru_cache.LRUSizeCache(max_size=10, after_cleanup_size=5)
        self.assertEqual(0, cache._value_size)
        self.assertEqual({}, cache.items())
        cache.add('test', 'key')
        self.assertEqual(3, cache._value_size)
        self.assertEqual({'test': 'key'}, cache.items())
        cache.add('test2', 'key that is too big')
        self.assertEqual(3, cache._value_size)
        self.assertEqual({'test':'key'}, cache.items())
        # If we would add a key, only to cleanup and remove all cached entries,
        # then obviously that value should not be stored
        cache.add('test3', 'bigkey')
        self.assertEqual(3, cache._value_size)
        self.assertEqual({'test':'key'}, cache.items())

        cache.add('test4', 'bikey')
        self.assertEqual(3, cache._value_size)
        self.assertEqual({'test':'key'}, cache.items())

    def test_no_add_over_size_cleanup(self):
        """If a large value is not cached, we will call cleanup right away."""
        cleanup_calls = []
        def cleanup(key, value):
            cleanup_calls.append((key, value))

        cache = lru_cache.LRUSizeCache(max_size=10, after_cleanup_size=5)
        self.assertEqual(0, cache._value_size)
        self.assertEqual({}, cache.items())
        cache.add('test', 'key that is too big', cleanup=cleanup)
        # key was not added
        self.assertEqual(0, cache._value_size)
        self.assertEqual({}, cache.items())
        # and cleanup was called
        self.assertEqual([('test', 'key that is too big')], cleanup_calls)

    def test_adding_clears_cache_based_on_size(self):
        """The cache is cleared in LRU order until small enough"""
        cache = lru_cache.LRUSizeCache(max_size=20)
        cache.add('key1', 'value') # 5 chars
        cache.add('key2', 'value2') # 6 chars
        cache.add('key3', 'value23') # 7 chars
        self.assertEqual(5+6+7, cache._value_size)
        cache['key2'] # reference key2 so it gets a newer reference time
        cache.add('key4', 'value234') # 8 chars, over limit
        # We have to remove 2 keys to get back under limit
        self.assertEqual(6+8, cache._value_size)
        self.assertEqual({'key2':'value2', 'key4':'value234'},
                         cache.items())

    def test_adding_clears_to_after_cleanup_size(self):
        cache = lru_cache.LRUSizeCache(max_size=20, after_cleanup_size=10)
        cache.add('key1', 'value') # 5 chars
        cache.add('key2', 'value2') # 6 chars
        cache.add('key3', 'value23') # 7 chars
        self.assertEqual(5+6+7, cache._value_size)
        cache['key2'] # reference key2 so it gets a newer reference time
        cache.add('key4', 'value234') # 8 chars, over limit
        # We have to remove 3 keys to get back under limit
        self.assertEqual(8, cache._value_size)
        self.assertEqual({'key4':'value234'}, cache.items())

    def test_custom_sizes(self):
        def size_of_list(lst):
            return sum(len(x) for x in lst)
        cache = lru_cache.LRUSizeCache(max_size=20, after_cleanup_size=10,
                                       compute_size=size_of_list)

        cache.add('key1', ['val', 'ue']) # 5 chars
        cache.add('key2', ['val', 'ue2']) # 6 chars
        cache.add('key3', ['val', 'ue23']) # 7 chars
        self.assertEqual(5+6+7, cache._value_size)
        cache['key2'] # reference key2 so it gets a newer reference time
        cache.add('key4', ['value', '234']) # 8 chars, over limit
        # We have to remove 3 keys to get back under limit
        self.assertEqual(8, cache._value_size)
        self.assertEqual({'key4':['value', '234']}, cache.items())

    def test_cleanup(self):
        cache = lru_cache.LRUSizeCache(max_size=20, after_cleanup_size=10)

        # Add these in order
        cache.add('key1', 'value') # 5 chars
        cache.add('key2', 'value2') # 6 chars
        cache.add('key3', 'value23') # 7 chars
        self.assertEqual(5+6+7, cache._value_size)

        cache.cleanup()
        # Only the most recent fits after cleaning up
        self.assertEqual(7, cache._value_size)

    def test_keys(self):
        cache = lru_cache.LRUSizeCache(max_size=10)

        cache[1] = 'a'
        cache[2] = 'b'
        cache[3] = 'cdef'
        self.assertEqual([1, 2, 3], sorted(cache.keys()))

    def test_resize_smaller(self):
        cache = lru_cache.LRUSizeCache(max_size=10, after_cleanup_size=9)
        cache[1] = 'abc'
        cache[2] = 'def'
        cache[3] = 'ghi'
        cache[4] = 'jkl'
        # Triggers a cleanup
        self.assertEqual([2, 3, 4], sorted(cache.keys()))
        # Resize should also cleanup again
        cache.resize(max_size=6, after_cleanup_size=4)
        self.assertEqual([4], sorted(cache.keys()))
        # Adding should use the new max size
        cache[5] = 'mno'
        self.assertEqual([4, 5], sorted(cache.keys()))
        cache[6] = 'pqr'
        self.assertEqual([6], sorted(cache.keys()))

    def test_resize_larger(self):
        cache = lru_cache.LRUSizeCache(max_size=10, after_cleanup_size=9)
        cache[1] = 'abc'
        cache[2] = 'def'
        cache[3] = 'ghi'
        cache[4] = 'jkl'
        # Triggers a cleanup
        self.assertEqual([2, 3, 4], sorted(cache.keys()))
        cache.resize(max_size=15, after_cleanup_size=12)
        self.assertEqual([2, 3, 4], sorted(cache.keys()))
        cache[5] = 'mno'
        cache[6] = 'pqr'
        self.assertEqual([2, 3, 4, 5, 6], sorted(cache.keys()))
        cache[7] = 'stu'
        self.assertEqual([4, 5, 6, 7], sorted(cache.keys()))


########NEW FILE########
__FILENAME__ = test_missing_obj_finder
# test_missing_obj_finder.py -- tests for MissingObjectFinder
# Copyright (C) 2012 syntevo GmbH
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

from dulwich.object_store import (
    MemoryObjectStore,
    )
from dulwich.objects import (
    Blob,
    )
from dulwich.tests import TestCase
from utils import (
    make_object,
    build_commit_graph,
    )


class MissingObjectFinderTest(TestCase):

    def setUp(self):
        super(MissingObjectFinderTest, self).setUp()
        self.store = MemoryObjectStore()
        self.commits = []

    def cmt(self, n):
        return self.commits[n-1]

    def assertMissingMatch(self, haves, wants, expected):
        for sha, path in self.store.find_missing_objects(haves, wants):
            self.assertTrue(sha in expected,
                "(%s,%s) erroneously reported as missing" % (sha, path))
            expected.remove(sha)

        self.assertEquals(len(expected), 0,
            "some objects are not reported as missing: %s" % (expected, ))


class MOFLinearRepoTest(MissingObjectFinderTest):

    def setUp(self):
        super(MOFLinearRepoTest, self).setUp()
        f1_1 = make_object(Blob, data='f1') # present in 1, removed in 3
        f2_1 = make_object(Blob, data='f2') # present in all revisions, changed in 2 and 3
        f2_2 = make_object(Blob, data='f2-changed')
        f2_3 = make_object(Blob, data='f2-changed-again')
        f3_2 = make_object(Blob, data='f3') # added in 2, left unmodified in 3

        commit_spec = [[1], [2, 1], [3, 2]]
        trees = {1: [('f1', f1_1), ('f2', f2_1)],
                2: [('f1', f1_1), ('f2', f2_2), ('f3', f3_2)],
                3: [('f2', f2_3), ('f3', f3_2)] }
        # commit 1: f1 and f2
        # commit 2: f3 added, f2 changed. Missing shall report commit id and a
        # tree referenced by commit
        # commit 3: f1 removed, f2 changed. Commit sha and root tree sha shall
        # be reported as modified
        self.commits = build_commit_graph(self.store, commit_spec, trees)
        self.missing_1_2 = [self.cmt(2).id, self.cmt(2).tree, f2_2.id, f3_2.id]
        self.missing_2_3 = [self.cmt(3).id, self.cmt(3).tree, f2_3.id]
        self.missing_1_3 = [
            self.cmt(2).id, self.cmt(3).id,
            self.cmt(2).tree, self.cmt(3).tree,
            f2_2.id, f3_2.id, f2_3.id]

    def test_1_to_2(self):
        self.assertMissingMatch([self.cmt(1).id], [self.cmt(2).id],
            self.missing_1_2)

    def test_2_to_3(self):
        self.assertMissingMatch([self.cmt(2).id], [self.cmt(3).id],
            self.missing_2_3)

    def test_1_to_3(self):
        self.assertMissingMatch([self.cmt(1).id], [self.cmt(3).id],
            self.missing_1_3)

    def test_bogus_haves_failure(self):
        """Ensure non-existent SHA in haves are not tolerated"""
        bogus_sha = self.cmt(2).id[::-1]
        haves = [self.cmt(1).id, bogus_sha]
        wants = [self.cmt(3).id]
        self.assertRaises(KeyError, self.store.find_missing_objects,
            self.store, haves, wants)

    def test_bogus_wants_failure(self):
        """Ensure non-existent SHA in wants are not tolerated"""
        bogus_sha = self.cmt(2).id[::-1]
        haves = [self.cmt(1).id]
        wants = [self.cmt(3).id, bogus_sha]
        self.assertRaises(KeyError, self.store.find_missing_objects,
            self.store, haves, wants)

    def test_no_changes(self):
        self.assertMissingMatch([self.cmt(3).id], [self.cmt(3).id], [])


class MOFMergeForkRepoTest(MissingObjectFinderTest):
    # 1 --- 2 --- 4 --- 6 --- 7
    #          \        /
    #           3  ---
    #            \
    #             5

    def setUp(self):
        super(MOFMergeForkRepoTest, self).setUp()
        f1_1 = make_object(Blob, data='f1')
        f1_2 = make_object(Blob, data='f1-2')
        f1_4 = make_object(Blob, data='f1-4')
        f1_7 = make_object(Blob, data='f1-2') # same data as in rev 2
        f2_1 = make_object(Blob, data='f2')
        f2_3 = make_object(Blob, data='f2-3')
        f3_3 = make_object(Blob, data='f3')
        f3_5 = make_object(Blob, data='f3-5')
        commit_spec = [[1], [2, 1], [3, 2], [4, 2], [5, 3], [6, 3, 4], [7, 6]]
        trees = {1: [('f1', f1_1), ('f2', f2_1)],
                2: [('f1', f1_2), ('f2', f2_1)], # f1 changed
                # f3 added, f2 changed
                3: [('f1', f1_2), ('f2', f2_3), ('f3', f3_3)],
                4: [('f1', f1_4), ('f2', f2_1)],  # f1 changed
                5: [('f1', f1_2), ('f3', f3_5)], # f2 removed, f3 changed
                6: [('f1', f1_4), ('f2', f2_3), ('f3', f3_3)], # merged 3 and 4
                # f1 changed to match rev2. f3 removed
                7: [('f1', f1_7), ('f2', f2_3)]}
        self.commits = build_commit_graph(self.store, commit_spec, trees)

        self.f1_2_id = f1_2.id
        self.f1_4_id = f1_4.id
        self.f1_7_id = f1_7.id
        self.f2_3_id = f2_3.id
        self.f3_3_id = f3_3.id

        self.assertEquals(f1_2.id, f1_7.id, "[sanity]")

    def test_have6_want7(self):
        # have 6, want 7. Ideally, shall not report f1_7 as it's the same as
        # f1_2, however, to do so, MissingObjectFinder shall not record trees
        # of common commits only, but also all parent trees and tree items,
        # which is an overkill (i.e. in sha_done it records f1_4 as known, and
        # doesn't record f1_2 was known prior to that, hence can't detect f1_7
        # is in fact f1_2 and shall not be reported)
        self.assertMissingMatch([self.cmt(6).id], [self.cmt(7).id],
            [self.cmt(7).id, self.cmt(7).tree, self.f1_7_id])

    def test_have4_want7(self):
        # have 4, want 7. Shall not include rev5 as it is not in the tree
        # between 4 and 7 (well, it is, but its SHA's are irrelevant for 4..7
        # commit hierarchy)
        self.assertMissingMatch([self.cmt(4).id], [self.cmt(7).id], [
            self.cmt(7).id, self.cmt(6).id, self.cmt(3).id,
            self.cmt(7).tree, self.cmt(6).tree, self.cmt(3).tree,
            self.f2_3_id, self.f3_3_id])

    def test_have1_want6(self):
        # have 1, want 6. Shall not include rev5
        self.assertMissingMatch([self.cmt(1).id], [self.cmt(6).id], [
            self.cmt(6).id, self.cmt(4).id, self.cmt(3).id, self.cmt(2).id,
            self.cmt(6).tree, self.cmt(4).tree, self.cmt(3).tree,
            self.cmt(2).tree, self.f1_2_id, self.f1_4_id, self.f2_3_id,
            self.f3_3_id])

    def test_have3_want6(self):
        # have 3, want 7. Shall not report rev2 and its tree, because
        # haves(3) means has parents, i.e. rev2, too
        # BUT shall report any changes descending rev2 (excluding rev3)
        # Shall NOT report f1_7 as it's techically == f1_2
        self.assertMissingMatch([self.cmt(3).id], [self.cmt(7).id], [
              self.cmt(7).id, self.cmt(6).id, self.cmt(4).id,
              self.cmt(7).tree, self.cmt(6).tree, self.cmt(4).tree,
              self.f1_4_id])

    def test_have5_want7(self):
        # have 5, want 7. Common parent is rev2, hence children of rev2 from
        # a descent line other than rev5 shall be reported
        # expects f1_4 from rev6. f3_5 is known in rev5;
        # f1_7 shall be the same as f1_2 (known, too)
        self.assertMissingMatch([self.cmt(5).id], [self.cmt(7).id], [
              self.cmt(7).id, self.cmt(6).id, self.cmt(4).id,
              self.cmt(7).tree, self.cmt(6).tree, self.cmt(4).tree,
              self.f1_4_id])

########NEW FILE########
__FILENAME__ = test_objects
# test_objects.py -- tests for objects.py
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for git base objects."""

# TODO: Round-trip parse-serialize-parse and serialize-parse-serialize tests.


from cStringIO import StringIO
import datetime
import os
import stat
import warnings

from dulwich.errors import (
    ObjectFormatException,
    )
from dulwich._compat import (
    permutations,
    )
from dulwich.objects import (
    Blob,
    Tree,
    Commit,
    ShaFile,
    Tag,
    format_timezone,
    hex_to_sha,
    sha_to_hex,
    hex_to_filename,
    check_hexsha,
    check_identity,
    parse_timezone,
    TreeEntry,
    parse_tree,
    _parse_tree_py,
    sorted_tree_items,
    _sorted_tree_items_py,
    )
from dulwich.tests import (
    TestCase,
    )
from utils import (
    make_commit,
    make_object,
    functest_builder,
    ext_functest_builder,
    )

a_sha = '6f670c0fb53f9463760b7295fbb814e965fb20c8'
b_sha = '2969be3e8ee1c0222396a5611407e4769f14e54b'
c_sha = '954a536f7819d40e6f637f849ee187dd10066349'
tree_sha = '70c190eb48fa8bbb50ddc692a17b44cb781af7f6'
tag_sha = '71033db03a03c6a36721efcf1968dd8f8e0cf023'


class TestHexToSha(TestCase):

    def test_simple(self):
        self.assertEqual("\xab\xcd" * 10, hex_to_sha("abcd" * 10))

    def test_reverse(self):
        self.assertEqual("abcd" * 10, sha_to_hex("\xab\xcd" * 10))


class BlobReadTests(TestCase):
    """Test decompression of blobs"""

    def get_sha_file(self, cls, base, sha):
        dir = os.path.join(os.path.dirname(__file__), 'data', base)
        return cls.from_path(hex_to_filename(dir, sha))

    def get_blob(self, sha):
        """Return the blob named sha from the test data dir"""
        return self.get_sha_file(Blob, 'blobs', sha)

    def get_tree(self, sha):
        return self.get_sha_file(Tree, 'trees', sha)

    def get_tag(self, sha):
        return self.get_sha_file(Tag, 'tags', sha)

    def commit(self, sha):
        return self.get_sha_file(Commit, 'commits', sha)

    def test_decompress_simple_blob(self):
        b = self.get_blob(a_sha)
        self.assertEqual(b.data, 'test 1\n')
        self.assertEqual(b.sha().hexdigest(), a_sha)

    def test_hash(self):
        b = self.get_blob(a_sha)
        self.assertEqual(hash(b.id), hash(b))

    def test_parse_empty_blob_object(self):
        sha = 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'
        b = self.get_blob(sha)
        self.assertEqual(b.data, '')
        self.assertEqual(b.id, sha)
        self.assertEqual(b.sha().hexdigest(), sha)

    def test_create_blob_from_string(self):
        string = 'test 2\n'
        b = Blob.from_string(string)
        self.assertEqual(b.data, string)
        self.assertEqual(b.sha().hexdigest(), b_sha)

    def test_legacy_from_file(self):
        b1 = Blob.from_string("foo")
        b_raw = b1.as_legacy_object()
        b2 = b1.from_file(StringIO(b_raw))
        self.assertEqual(b1, b2)

    def test_chunks(self):
        string = 'test 5\n'
        b = Blob.from_string(string)
        self.assertEqual([string], b.chunked)

    def test_set_chunks(self):
        b = Blob()
        b.chunked = ['te', 'st', ' 5\n']
        self.assertEqual('test 5\n', b.data)
        b.chunked = ['te', 'st', ' 6\n']
        self.assertEqual('test 6\n', b.as_raw_string())

    def test_parse_legacy_blob(self):
        string = 'test 3\n'
        b = self.get_blob(c_sha)
        self.assertEqual(b.data, string)
        self.assertEqual(b.sha().hexdigest(), c_sha)

    def test_eq(self):
        blob1 = self.get_blob(a_sha)
        blob2 = self.get_blob(a_sha)
        self.assertEqual(blob1, blob2)

    def test_read_tree_from_file(self):
        t = self.get_tree(tree_sha)
        self.assertEqual(t.items()[0], ('a', 33188, a_sha))
        self.assertEqual(t.items()[1], ('b', 33188, b_sha))

    def test_read_tag_from_file(self):
        t = self.get_tag(tag_sha)
        self.assertEqual(t.object,
            (Commit, '51b668fd5bf7061b7d6fa525f88803e6cfadaa51'))
        self.assertEqual(t.name,'signed')
        self.assertEqual(t.tagger,'Ali Sabil <ali.sabil@gmail.com>')
        self.assertEqual(t.tag_time, 1231203091)
        self.assertEqual(t.message, 'This is a signed tag\n-----BEGIN PGP SIGNATURE-----\nVersion: GnuPG v1.4.9 (GNU/Linux)\n\niEYEABECAAYFAkliqx8ACgkQqSMmLy9u/kcx5ACfakZ9NnPl02tOyYP6pkBoEkU1\n5EcAn0UFgokaSvS371Ym/4W9iJj6vh3h\n=ql7y\n-----END PGP SIGNATURE-----\n')

    def test_read_commit_from_file(self):
        sha = '60dacdc733de308bb77bb76ce0fb0f9b44c9769e'
        c = self.commit(sha)
        self.assertEqual(c.tree, tree_sha)
        self.assertEqual(c.parents,
            ['0d89f20333fbb1d2f3a94da77f4981373d8f4310'])
        self.assertEqual(c.author,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.committer,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.commit_time, 1174759230)
        self.assertEqual(c.commit_timezone, 0)
        self.assertEqual(c.author_timezone, 0)
        self.assertEqual(c.message, 'Test commit\n')

    def test_read_commit_no_parents(self):
        sha = '0d89f20333fbb1d2f3a94da77f4981373d8f4310'
        c = self.commit(sha)
        self.assertEqual(c.tree, '90182552c4a85a45ec2a835cadc3451bebdfe870')
        self.assertEqual(c.parents, [])
        self.assertEqual(c.author,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.committer,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.commit_time, 1174758034)
        self.assertEqual(c.commit_timezone, 0)
        self.assertEqual(c.author_timezone, 0)
        self.assertEqual(c.message, 'Test commit\n')

    def test_read_commit_two_parents(self):
        sha = '5dac377bdded4c9aeb8dff595f0faeebcc8498cc'
        c = self.commit(sha)
        self.assertEqual(c.tree, 'd80c186a03f423a81b39df39dc87fd269736ca86')
        self.assertEqual(c.parents, ['ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                                       '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'])
        self.assertEqual(c.author,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.committer,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.commit_time, 1174773719)
        self.assertEqual(c.commit_timezone, 0)
        self.assertEqual(c.author_timezone, 0)
        self.assertEqual(c.message, 'Merge ../b\n')

    def test_stub_sha(self):
        sha = '5' * 40
        c = make_commit(id=sha, message='foo')
        self.assertTrue(isinstance(c, Commit))
        self.assertEqual(sha, c.id)
        self.assertNotEqual(sha, c._make_sha())


class ShaFileCheckTests(TestCase):

    def assertCheckFails(self, cls, data):
        obj = cls()
        def do_check():
            obj.set_raw_string(data)
            obj.check()
        self.assertRaises(ObjectFormatException, do_check)

    def assertCheckSucceeds(self, cls, data):
        obj = cls()
        obj.set_raw_string(data)
        self.assertEqual(None, obj.check())


small_buffer_zlib_object = (
 "\x48\x89\x15\xcc\x31\x0e\xc2\x30\x0c\x40\x51\xe6"
 "\x9c\xc2\x3b\xaa\x64\x37\xc4\xc1\x12\x42\x5c\xc5"
 "\x49\xac\x52\xd4\x92\xaa\x78\xe1\xf6\x94\xed\xeb"
 "\x0d\xdf\x75\x02\xa2\x7c\xea\xe5\x65\xd5\x81\x8b"
 "\x9a\x61\xba\xa0\xa9\x08\x36\xc9\x4c\x1a\xad\x88"
 "\x16\xba\x46\xc4\xa8\x99\x6a\x64\xe1\xe0\xdf\xcd"
 "\xa0\xf6\x75\x9d\x3d\xf8\xf1\xd0\x77\xdb\xfb\xdc"
 "\x86\xa3\x87\xf1\x2f\x93\xed\x00\xb7\xc7\xd2\xab"
 "\x2e\xcf\xfe\xf1\x3b\x50\xa4\x91\x53\x12\x24\x38"
 "\x23\x21\x86\xf0\x03\x2f\x91\x24\x52"
 )


class ShaFileTests(TestCase):

    def test_deflated_smaller_window_buffer(self):
        # zlib on some systems uses smaller buffers,
        # resulting in a different header.
        # See https://github.com/libgit2/libgit2/pull/464
        sf = ShaFile.from_file(StringIO(small_buffer_zlib_object))
        self.assertEqual(sf.type_name, "tag")
        self.assertEqual(sf.tagger, " <@localhost>")


class CommitSerializationTests(TestCase):

    def make_commit(self, **kwargs):
        attrs = {'tree': 'd80c186a03f423a81b39df39dc87fd269736ca86',
                 'parents': ['ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                             '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'],
                 'author': 'James Westby <jw+debian@jameswestby.net>',
                 'committer': 'James Westby <jw+debian@jameswestby.net>',
                 'commit_time': 1174773719,
                 'author_time': 1174773719,
                 'commit_timezone': 0,
                 'author_timezone': 0,
                 'message':  'Merge ../b\n'}
        attrs.update(kwargs)
        return make_commit(**attrs)

    def test_encoding(self):
        c = self.make_commit(encoding='iso8859-1')
        self.assertTrue('encoding iso8859-1\n' in c.as_raw_string())

    def test_short_timestamp(self):
        c = self.make_commit(commit_time=30)
        c1 = Commit()
        c1.set_raw_string(c.as_raw_string())
        self.assertEqual(30, c1.commit_time)

    def test_raw_length(self):
        c = self.make_commit()
        self.assertEqual(len(c.as_raw_string()), c.raw_length())

    def test_simple(self):
        c = self.make_commit()
        self.assertEqual(c.id, '5dac377bdded4c9aeb8dff595f0faeebcc8498cc')
        self.assertEqual(
                'tree d80c186a03f423a81b39df39dc87fd269736ca86\n'
                'parent ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd\n'
                'parent 4cffe90e0a41ad3f5190079d7c8f036bde29cbe6\n'
                'author James Westby <jw+debian@jameswestby.net> '
                '1174773719 +0000\n'
                'committer James Westby <jw+debian@jameswestby.net> '
                '1174773719 +0000\n'
                '\n'
                'Merge ../b\n', c.as_raw_string())

    def test_timezone(self):
        c = self.make_commit(commit_timezone=(5 * 60))
        self.assertTrue(" +0005\n" in c.as_raw_string())

    def test_neg_timezone(self):
        c = self.make_commit(commit_timezone=(-1 * 3600))
        self.assertTrue(" -0100\n" in c.as_raw_string())

    def test_deserialize(self):
        c = self.make_commit()
        d = Commit()
        d._deserialize(c.as_raw_chunks())
        self.assertEqual(c, d)

    def test_serialize_mergetag(self):
        tag = make_object(
            Tag, object=(Commit, "a38d6181ff27824c79fc7df825164a212eff6a3f"),
            object_type_name="commit",
            name="v2.6.22-rc7",
            tag_time=1183319674,
            tag_timezone=0,
            tagger="Linus Torvalds <torvalds@woody.linux-foundation.org>",
            message=default_message)
        commit = self.make_commit(mergetag=[tag])

        self.assertEqual("""tree d80c186a03f423a81b39df39dc87fd269736ca86
parent ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd
parent 4cffe90e0a41ad3f5190079d7c8f036bde29cbe6
author James Westby <jw+debian@jameswestby.net> 1174773719 +0000
committer James Westby <jw+debian@jameswestby.net> 1174773719 +0000
mergetag object a38d6181ff27824c79fc7df825164a212eff6a3f
 type commit
 tag v2.6.22-rc7
 tagger Linus Torvalds <torvalds@woody.linux-foundation.org> 1183319674 +0000
 
 Linux 2.6.22-rc7
 -----BEGIN PGP SIGNATURE-----
 Version: GnuPG v1.4.7 (GNU/Linux)
 
 iD8DBQBGiAaAF3YsRnbiHLsRAitMAKCiLboJkQECM/jpYsY3WPfvUgLXkACgg3ql
 OK2XeQOiEeXtT76rV4t2WR4=
 =ivrA
 -----END PGP SIGNATURE-----

Merge ../b
""", commit.as_raw_string())

    def test_serialize_mergetags(self):
        tag = make_object(
            Tag, object=(Commit, "a38d6181ff27824c79fc7df825164a212eff6a3f"),
            object_type_name="commit",
            name="v2.6.22-rc7",
            tag_time=1183319674,
            tag_timezone=0,
            tagger="Linus Torvalds <torvalds@woody.linux-foundation.org>",
            message=default_message)
        commit = self.make_commit(mergetag=[tag, tag])

        self.assertEqual("""tree d80c186a03f423a81b39df39dc87fd269736ca86
parent ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd
parent 4cffe90e0a41ad3f5190079d7c8f036bde29cbe6
author James Westby <jw+debian@jameswestby.net> 1174773719 +0000
committer James Westby <jw+debian@jameswestby.net> 1174773719 +0000
mergetag object a38d6181ff27824c79fc7df825164a212eff6a3f
 type commit
 tag v2.6.22-rc7
 tagger Linus Torvalds <torvalds@woody.linux-foundation.org> 1183319674 +0000
 
 Linux 2.6.22-rc7
 -----BEGIN PGP SIGNATURE-----
 Version: GnuPG v1.4.7 (GNU/Linux)
 
 iD8DBQBGiAaAF3YsRnbiHLsRAitMAKCiLboJkQECM/jpYsY3WPfvUgLXkACgg3ql
 OK2XeQOiEeXtT76rV4t2WR4=
 =ivrA
 -----END PGP SIGNATURE-----
mergetag object a38d6181ff27824c79fc7df825164a212eff6a3f
 type commit
 tag v2.6.22-rc7
 tagger Linus Torvalds <torvalds@woody.linux-foundation.org> 1183319674 +0000
 
 Linux 2.6.22-rc7
 -----BEGIN PGP SIGNATURE-----
 Version: GnuPG v1.4.7 (GNU/Linux)
 
 iD8DBQBGiAaAF3YsRnbiHLsRAitMAKCiLboJkQECM/jpYsY3WPfvUgLXkACgg3ql
 OK2XeQOiEeXtT76rV4t2WR4=
 =ivrA
 -----END PGP SIGNATURE-----

Merge ../b
""", commit.as_raw_string())

    def test_deserialize_mergetag(self):
        tag = make_object(
            Tag, object=(Commit, "a38d6181ff27824c79fc7df825164a212eff6a3f"),
            object_type_name="commit",
            name="v2.6.22-rc7",
            tag_time=1183319674,
            tag_timezone=0,
            tagger="Linus Torvalds <torvalds@woody.linux-foundation.org>",
            message=default_message)
        commit = self.make_commit(mergetag=[tag])

        d = Commit()
        d._deserialize(commit.as_raw_chunks())
        self.assertEqual(commit, d)

    def test_deserialize_mergetags(self):
        tag = make_object(
            Tag, object=(Commit, "a38d6181ff27824c79fc7df825164a212eff6a3f"),
            object_type_name="commit",
            name="v2.6.22-rc7",
            tag_time=1183319674,
            tag_timezone=0,
            tagger="Linus Torvalds <torvalds@woody.linux-foundation.org>",
            message=default_message)
        commit = self.make_commit(mergetag=[tag, tag])

        d = Commit()
        d._deserialize(commit.as_raw_chunks())
        self.assertEquals(commit, d)


default_committer = 'James Westby <jw+debian@jameswestby.net> 1174773719 +0000'

class CommitParseTests(ShaFileCheckTests):

    def make_commit_lines(self,
                          tree='d80c186a03f423a81b39df39dc87fd269736ca86',
                          parents=['ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                                   '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'],
                          author=default_committer,
                          committer=default_committer,
                          encoding=None,
                          message='Merge ../b\n',
                          extra=None):
        lines = []
        if tree is not None:
            lines.append('tree %s' % tree)
        if parents is not None:
            lines.extend('parent %s' % p for p in parents)
        if author is not None:
            lines.append('author %s' % author)
        if committer is not None:
            lines.append('committer %s' % committer)
        if encoding is not None:
            lines.append('encoding %s' % encoding)
        if extra is not None:
            for name, value in sorted(extra.iteritems()):
                lines.append('%s %s' % (name, value))
        lines.append('')
        if message is not None:
            lines.append(message)
        return lines

    def make_commit_text(self, **kwargs):
        return '\n'.join(self.make_commit_lines(**kwargs))

    def test_simple(self):
        c = Commit.from_string(self.make_commit_text())
        self.assertEqual('Merge ../b\n', c.message)
        self.assertEqual('James Westby <jw+debian@jameswestby.net>', c.author)
        self.assertEqual('James Westby <jw+debian@jameswestby.net>',
                          c.committer)
        self.assertEqual('d80c186a03f423a81b39df39dc87fd269736ca86', c.tree)
        self.assertEqual(['ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                           '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'],
                          c.parents)
        expected_time = datetime.datetime(2007, 3, 24, 22, 1, 59)
        self.assertEqual(expected_time,
                          datetime.datetime.utcfromtimestamp(c.commit_time))
        self.assertEqual(0, c.commit_timezone)
        self.assertEqual(expected_time,
                          datetime.datetime.utcfromtimestamp(c.author_time))
        self.assertEqual(0, c.author_timezone)
        self.assertEqual(None, c.encoding)

    def test_custom(self):
        c = Commit.from_string(self.make_commit_text(
          extra={'extra-field': 'data'}))
        self.assertEqual([('extra-field', 'data')], c.extra)

    def test_encoding(self):
        c = Commit.from_string(self.make_commit_text(encoding='UTF-8'))
        self.assertEqual('UTF-8', c.encoding)

    def test_check(self):
        self.assertCheckSucceeds(Commit, self.make_commit_text())
        self.assertCheckSucceeds(Commit, self.make_commit_text(parents=None))
        self.assertCheckSucceeds(Commit,
                                 self.make_commit_text(encoding='UTF-8'))

        self.assertCheckFails(Commit, self.make_commit_text(tree='xxx'))
        self.assertCheckFails(Commit, self.make_commit_text(
          parents=[a_sha, 'xxx']))
        bad_committer = "some guy without an email address 1174773719 +0000"
        self.assertCheckFails(Commit,
                              self.make_commit_text(committer=bad_committer))
        self.assertCheckFails(Commit,
                              self.make_commit_text(author=bad_committer))
        self.assertCheckFails(Commit, self.make_commit_text(author=None))
        self.assertCheckFails(Commit, self.make_commit_text(committer=None))
        self.assertCheckFails(Commit, self.make_commit_text(
          author=None, committer=None))

    def test_check_duplicates(self):
        # duplicate each of the header fields
        for i in xrange(5):
            lines = self.make_commit_lines(parents=[a_sha], encoding='UTF-8')
            lines.insert(i, lines[i])
            text = '\n'.join(lines)
            if lines[i].startswith('parent'):
                # duplicate parents are ok for now
                self.assertCheckSucceeds(Commit, text)
            else:
                self.assertCheckFails(Commit, text)

    def test_check_order(self):
        lines = self.make_commit_lines(parents=[a_sha], encoding='UTF-8')
        headers = lines[:5]
        rest = lines[5:]
        # of all possible permutations, ensure only the original succeeds
        for perm in permutations(headers):
            perm = list(perm)
            text = '\n'.join(perm + rest)
            if perm == headers:
                self.assertCheckSucceeds(Commit, text)
            else:
                self.assertCheckFails(Commit, text)


_TREE_ITEMS = {
  'a.c': (0100755, 'd80c186a03f423a81b39df39dc87fd269736ca86'),
  'a': (stat.S_IFDIR, 'd80c186a03f423a81b39df39dc87fd269736ca86'),
  'a/c': (stat.S_IFDIR, 'd80c186a03f423a81b39df39dc87fd269736ca86'),
  }

_SORTED_TREE_ITEMS = [
  TreeEntry('a.c', 0100755, 'd80c186a03f423a81b39df39dc87fd269736ca86'),
  TreeEntry('a', stat.S_IFDIR, 'd80c186a03f423a81b39df39dc87fd269736ca86'),
  TreeEntry('a/c', stat.S_IFDIR, 'd80c186a03f423a81b39df39dc87fd269736ca86'),
  ]


class TreeTests(ShaFileCheckTests):

    def test_add(self):
        myhexsha = "d80c186a03f423a81b39df39dc87fd269736ca86"
        x = Tree()
        x.add("myname", 0100755, myhexsha)
        self.assertEqual(x["myname"], (0100755, myhexsha))
        self.assertEqual('100755 myname\0' + hex_to_sha(myhexsha),
                x.as_raw_string())

    def test_add_old_order(self):
        myhexsha = "d80c186a03f423a81b39df39dc87fd269736ca86"
        x = Tree()
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            x.add(0100755, "myname", myhexsha)
        finally:
            warnings.resetwarnings()
        self.assertEqual(x["myname"], (0100755, myhexsha))
        self.assertEqual('100755 myname\0' + hex_to_sha(myhexsha),
                x.as_raw_string())

    def test_simple(self):
        myhexsha = "d80c186a03f423a81b39df39dc87fd269736ca86"
        x = Tree()
        x["myname"] = (0100755, myhexsha)
        self.assertEqual('100755 myname\0' + hex_to_sha(myhexsha),
                x.as_raw_string())

    def test_tree_update_id(self):
        x = Tree()
        x["a.c"] = (0100755, "d80c186a03f423a81b39df39dc87fd269736ca86")
        self.assertEqual("0c5c6bc2c081accfbc250331b19e43b904ab9cdd", x.id)
        x["a.b"] = (stat.S_IFDIR, "d80c186a03f423a81b39df39dc87fd269736ca86")
        self.assertEqual("07bfcb5f3ada15bbebdfa3bbb8fd858a363925c8", x.id)

    def test_tree_iteritems_dir_sort(self):
        x = Tree()
        for name, item in _TREE_ITEMS.iteritems():
            x[name] = item
        self.assertEqual(_SORTED_TREE_ITEMS, list(x.iteritems()))

    def test_tree_items_dir_sort(self):
        x = Tree()
        for name, item in _TREE_ITEMS.iteritems():
            x[name] = item
        self.assertEqual(_SORTED_TREE_ITEMS, x.items())

    def _do_test_parse_tree(self, parse_tree):
        dir = os.path.join(os.path.dirname(__file__), 'data', 'trees')
        o = Tree.from_path(hex_to_filename(dir, tree_sha))
        self.assertEqual([('a', 0100644, a_sha), ('b', 0100644, b_sha)],
                          list(parse_tree(o.as_raw_string())))
        # test a broken tree that has a leading 0 on the file mode
        broken_tree = '0100644 foo\0' + hex_to_sha(a_sha)

        def eval_parse_tree(*args, **kwargs):
            return list(parse_tree(*args, **kwargs))

        self.assertEqual([('foo', 0100644, a_sha)],
                          eval_parse_tree(broken_tree))
        self.assertRaises(ObjectFormatException,
                          eval_parse_tree, broken_tree, strict=True)

    test_parse_tree = functest_builder(_do_test_parse_tree, _parse_tree_py)
    test_parse_tree_extension = ext_functest_builder(_do_test_parse_tree,
                                                     parse_tree)

    def _do_test_sorted_tree_items(self, sorted_tree_items):
        def do_sort(entries):
            return list(sorted_tree_items(entries, False))

        actual = do_sort(_TREE_ITEMS)
        self.assertEqual(_SORTED_TREE_ITEMS, actual)
        self.assertTrue(isinstance(actual[0], TreeEntry))

        # C/Python implementations may differ in specific error types, but
        # should all error on invalid inputs.
        # For example, the C implementation has stricter type checks, so may
        # raise TypeError where the Python implementation raises AttributeError.
        errors = (TypeError, ValueError, AttributeError)
        self.assertRaises(errors, do_sort, 'foo')
        self.assertRaises(errors, do_sort, {'foo': (1, 2, 3)})

        myhexsha = 'd80c186a03f423a81b39df39dc87fd269736ca86'
        self.assertRaises(errors, do_sort, {'foo': ('xxx', myhexsha)})
        self.assertRaises(errors, do_sort, {'foo': (0100755, 12345)})

    test_sorted_tree_items = functest_builder(_do_test_sorted_tree_items,
                                              _sorted_tree_items_py)
    test_sorted_tree_items_extension = ext_functest_builder(
      _do_test_sorted_tree_items, sorted_tree_items)

    def _do_test_sorted_tree_items_name_order(self, sorted_tree_items):
        self.assertEqual([
          TreeEntry('a', stat.S_IFDIR,
                    'd80c186a03f423a81b39df39dc87fd269736ca86'),
          TreeEntry('a.c', 0100755, 'd80c186a03f423a81b39df39dc87fd269736ca86'),
          TreeEntry('a/c', stat.S_IFDIR,
                    'd80c186a03f423a81b39df39dc87fd269736ca86'),
          ], list(sorted_tree_items(_TREE_ITEMS, True)))

    test_sorted_tree_items_name_order = functest_builder(
      _do_test_sorted_tree_items_name_order, _sorted_tree_items_py)
    test_sorted_tree_items_name_order_extension = ext_functest_builder(
      _do_test_sorted_tree_items_name_order, sorted_tree_items)

    def test_check(self):
        t = Tree
        sha = hex_to_sha(a_sha)

        # filenames
        self.assertCheckSucceeds(t, '100644 .a\0%s' % sha)
        self.assertCheckFails(t, '100644 \0%s' % sha)
        self.assertCheckFails(t, '100644 .\0%s' % sha)
        self.assertCheckFails(t, '100644 a/a\0%s' % sha)
        self.assertCheckFails(t, '100644 ..\0%s' % sha)

        # modes
        self.assertCheckSucceeds(t, '100644 a\0%s' % sha)
        self.assertCheckSucceeds(t, '100755 a\0%s' % sha)
        self.assertCheckSucceeds(t, '160000 a\0%s' % sha)
        # TODO more whitelisted modes
        self.assertCheckFails(t, '123456 a\0%s' % sha)
        self.assertCheckFails(t, '123abc a\0%s' % sha)
        # should fail check, but parses ok
        self.assertCheckFails(t, '0100644 foo\0' + sha)

        # shas
        self.assertCheckFails(t, '100644 a\0%s' % ('x' * 5))
        self.assertCheckFails(t, '100644 a\0%s' % ('x' * 18 + '\0'))
        self.assertCheckFails(t, '100644 a\0%s\n100644 b\0%s' % ('x' * 21, sha))

        # ordering
        sha2 = hex_to_sha(b_sha)
        self.assertCheckSucceeds(t, '100644 a\0%s\n100644 b\0%s' % (sha, sha))
        self.assertCheckSucceeds(t, '100644 a\0%s\n100644 b\0%s' % (sha, sha2))
        self.assertCheckFails(t, '100644 a\0%s\n100755 a\0%s' % (sha, sha2))
        self.assertCheckFails(t, '100644 b\0%s\n100644 a\0%s' % (sha2, sha))

    def test_iter(self):
        t = Tree()
        t["foo"] = (0100644, a_sha)
        self.assertEqual(set(["foo"]), set(t))


class TagSerializeTests(TestCase):

    def test_serialize_simple(self):
        x = make_object(Tag,
                        tagger='Jelmer Vernooij <jelmer@samba.org>',
                        name='0.1',
                        message='Tag 0.1',
                        object=(Blob, 'd80c186a03f423a81b39df39dc87fd269736ca86'),
                        tag_time=423423423,
                        tag_timezone=0)
        self.assertEqual(('object d80c186a03f423a81b39df39dc87fd269736ca86\n'
                           'type blob\n'
                           'tag 0.1\n'
                           'tagger Jelmer Vernooij <jelmer@samba.org> '
                           '423423423 +0000\n'
                           '\n'
                           'Tag 0.1'), x.as_raw_string())


default_tagger = ('Linus Torvalds <torvalds@woody.linux-foundation.org> '
                  '1183319674 -0700')
default_message = """Linux 2.6.22-rc7
-----BEGIN PGP SIGNATURE-----
Version: GnuPG v1.4.7 (GNU/Linux)

iD8DBQBGiAaAF3YsRnbiHLsRAitMAKCiLboJkQECM/jpYsY3WPfvUgLXkACgg3ql
OK2XeQOiEeXtT76rV4t2WR4=
=ivrA
-----END PGP SIGNATURE-----
"""


class TagParseTests(ShaFileCheckTests):

    def make_tag_lines(self,
                       object_sha="a38d6181ff27824c79fc7df825164a212eff6a3f",
                       object_type_name="commit",
                       name="v2.6.22-rc7",
                       tagger=default_tagger,
                       message=default_message):
        lines = []
        if object_sha is not None:
            lines.append("object %s" % object_sha)
        if object_type_name is not None:
            lines.append("type %s" % object_type_name)
        if name is not None:
            lines.append("tag %s" % name)
        if tagger is not None:
            lines.append("tagger %s" % tagger)
        lines.append("")
        if message is not None:
            lines.append(message)
        return lines

    def make_tag_text(self, **kwargs):
        return "\n".join(self.make_tag_lines(**kwargs))

    def test_parse(self):
        x = Tag()
        x.set_raw_string(self.make_tag_text())
        self.assertEqual(
            "Linus Torvalds <torvalds@woody.linux-foundation.org>", x.tagger)
        self.assertEqual("v2.6.22-rc7", x.name)
        object_type, object_sha = x.object
        self.assertEqual("a38d6181ff27824c79fc7df825164a212eff6a3f",
                          object_sha)
        self.assertEqual(Commit, object_type)
        self.assertEqual(datetime.datetime.utcfromtimestamp(x.tag_time),
                          datetime.datetime(2007, 7, 1, 19, 54, 34))
        self.assertEqual(-25200, x.tag_timezone)

    def test_parse_no_tagger(self):
        x = Tag()
        x.set_raw_string(self.make_tag_text(tagger=None))
        self.assertEqual(None, x.tagger)
        self.assertEqual("v2.6.22-rc7", x.name)

    def test_check(self):
        self.assertCheckSucceeds(Tag, self.make_tag_text())
        self.assertCheckFails(Tag, self.make_tag_text(object_sha=None))
        self.assertCheckFails(Tag, self.make_tag_text(object_type_name=None))
        self.assertCheckFails(Tag, self.make_tag_text(name=None))
        self.assertCheckFails(Tag, self.make_tag_text(name=''))
        self.assertCheckFails(Tag, self.make_tag_text(
          object_type_name="foobar"))
        self.assertCheckFails(Tag, self.make_tag_text(
          tagger="some guy without an email address 1183319674 -0700"))
        self.assertCheckFails(Tag, self.make_tag_text(
          tagger=("Linus Torvalds <torvalds@woody.linux-foundation.org> "
                  "Sun 7 Jul 2007 12:54:34 +0700")))
        self.assertCheckFails(Tag, self.make_tag_text(object_sha="xxx"))

    def test_check_duplicates(self):
        # duplicate each of the header fields
        for i in xrange(4):
            lines = self.make_tag_lines()
            lines.insert(i, lines[i])
            self.assertCheckFails(Tag, '\n'.join(lines))

    def test_check_order(self):
        lines = self.make_tag_lines()
        headers = lines[:4]
        rest = lines[4:]
        # of all possible permutations, ensure only the original succeeds
        for perm in permutations(headers):
            perm = list(perm)
            text = '\n'.join(perm + rest)
            if perm == headers:
                self.assertCheckSucceeds(Tag, text)
            else:
                self.assertCheckFails(Tag, text)


class CheckTests(TestCase):

    def test_check_hexsha(self):
        check_hexsha(a_sha, "failed to check good sha")
        self.assertRaises(ObjectFormatException, check_hexsha, '1' * 39,
                          'sha too short')
        self.assertRaises(ObjectFormatException, check_hexsha, '1' * 41,
                          'sha too long')
        self.assertRaises(ObjectFormatException, check_hexsha, 'x' * 40,
                          'invalid characters')

    def test_check_identity(self):
        check_identity("Dave Borowitz <dborowitz@google.com>",
                       "failed to check good identity")
        check_identity("<dborowitz@google.com>",
                       "failed to check good identity")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz", "no email")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz <dborowitz", "incomplete email")
        self.assertRaises(ObjectFormatException, check_identity,
                          "dborowitz@google.com>", "incomplete email")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz <<dborowitz@google.com>", "typo")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz <dborowitz@google.com>>", "typo")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz <dborowitz@google.com>xxx",
                          "trailing characters")


class TimezoneTests(TestCase):

    def test_parse_timezone_utc(self):
        self.assertEqual((0, False), parse_timezone("+0000"))

    def test_parse_timezone_utc_negative(self):
        self.assertEqual((0, True), parse_timezone("-0000"))

    def test_generate_timezone_utc(self):
        self.assertEqual("+0000", format_timezone(0))

    def test_generate_timezone_utc_negative(self):
        self.assertEqual("-0000", format_timezone(0, True))

    def test_parse_timezone_cet(self):
        self.assertEqual((60 * 60, False), parse_timezone("+0100"))

    def test_format_timezone_cet(self):
        self.assertEqual("+0100", format_timezone(60 * 60))

    def test_format_timezone_pdt(self):
        self.assertEqual("-0400", format_timezone(-4 * 60 * 60))

    def test_parse_timezone_pdt(self):
        self.assertEqual((-4 * 60 * 60, False), parse_timezone("-0400"))

    def test_format_timezone_pdt_half(self):
        self.assertEqual("-0440",
            format_timezone(int(((-4 * 60) - 40) * 60)))

    def test_format_timezone_double_negative(self):
        self.assertEqual("--700",
            format_timezone(int(((7 * 60)) * 60), True))

    def test_parse_timezone_pdt_half(self):
        self.assertEqual((((-4 * 60) - 40) * 60, False),
            parse_timezone("-0440"))

    def test_parse_timezone_double_negative(self):
        self.assertEqual(
            (int(((7 * 60)) * 60), False), parse_timezone("+700"))
        self.assertEqual(
            (int(((7 * 60)) * 60), True), parse_timezone("--700"))

########NEW FILE########
__FILENAME__ = test_object_store
# test_object_store.py -- tests for object_store.py
# Copyright (C) 2008 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for the object store interface."""


from cStringIO import StringIO
import os
import shutil
import tempfile

from dulwich.index import (
    commit_tree,
    )
from dulwich.errors import (
    NotTreeError,
    )
from dulwich.objects import (
    sha_to_hex,
    object_class,
    Blob,
    Tag,
    Tree,
    TreeEntry,
    )
from dulwich.object_store import (
    DiskObjectStore,
    MemoryObjectStore,
    ObjectStoreGraphWalker,
    tree_lookup_path,
    )
from dulwich.pack import (
    REF_DELTA,
    write_pack_objects,
    )
from dulwich.tests import (
    TestCase,
    )
from dulwich.tests.utils import (
    make_object,
    build_pack,
    )


testobject = make_object(Blob, data="yummy data")


class ObjectStoreTests(object):

    def test_determine_wants_all(self):
        self.assertEqual(["1" * 40],
            self.store.determine_wants_all({"refs/heads/foo": "1" * 40}))

    def test_determine_wants_all_zero(self):
        self.assertEqual([],
            self.store.determine_wants_all({"refs/heads/foo": "0" * 40}))

    def test_iter(self):
        self.assertEqual([], list(self.store))

    def test_get_nonexistant(self):
        self.assertRaises(KeyError, lambda: self.store["a" * 40])

    def test_contains_nonexistant(self):
        self.assertFalse(("a" * 40) in self.store)

    def test_add_objects_empty(self):
        self.store.add_objects([])

    def test_add_commit(self):
        # TODO: Argh, no way to construct Git commit objects without 
        # access to a serialized form.
        self.store.add_objects([])

    def test_add_object(self):
        self.store.add_object(testobject)
        self.assertEqual(set([testobject.id]), set(self.store))
        self.assertTrue(testobject.id in self.store)
        r = self.store[testobject.id]
        self.assertEqual(r, testobject)

    def test_add_objects(self):
        data = [(testobject, "mypath")]
        self.store.add_objects(data)
        self.assertEqual(set([testobject.id]), set(self.store))
        self.assertTrue(testobject.id in self.store)
        r = self.store[testobject.id]
        self.assertEqual(r, testobject)

    def test_tree_changes(self):
        blob_a1 = make_object(Blob, data='a1')
        blob_a2 = make_object(Blob, data='a2')
        blob_b = make_object(Blob, data='b')
        for blob in [blob_a1, blob_a2, blob_b]:
            self.store.add_object(blob)

        blobs_1 = [('a', blob_a1.id, 0100644), ('b', blob_b.id, 0100644)]
        tree1_id = commit_tree(self.store, blobs_1)
        blobs_2 = [('a', blob_a2.id, 0100644), ('b', blob_b.id, 0100644)]
        tree2_id = commit_tree(self.store, blobs_2)
        change_a = (('a', 'a'), (0100644, 0100644), (blob_a1.id, blob_a2.id))
        self.assertEqual([change_a],
                          list(self.store.tree_changes(tree1_id, tree2_id)))
        self.assertEqual(
          [change_a, (('b', 'b'), (0100644, 0100644), (blob_b.id, blob_b.id))],
          list(self.store.tree_changes(tree1_id, tree2_id,
                                       want_unchanged=True)))

    def test_iter_tree_contents(self):
        blob_a = make_object(Blob, data='a')
        blob_b = make_object(Blob, data='b')
        blob_c = make_object(Blob, data='c')
        for blob in [blob_a, blob_b, blob_c]:
            self.store.add_object(blob)

        blobs = [
          ('a', blob_a.id, 0100644),
          ('ad/b', blob_b.id, 0100644),
          ('ad/bd/c', blob_c.id, 0100755),
          ('ad/c', blob_c.id, 0100644),
          ('c', blob_c.id, 0100644),
          ]
        tree_id = commit_tree(self.store, blobs)
        self.assertEqual([TreeEntry(p, m, h) for (p, h, m) in blobs],
                          list(self.store.iter_tree_contents(tree_id)))

    def test_iter_tree_contents_include_trees(self):
        blob_a = make_object(Blob, data='a')
        blob_b = make_object(Blob, data='b')
        blob_c = make_object(Blob, data='c')
        for blob in [blob_a, blob_b, blob_c]:
            self.store.add_object(blob)

        blobs = [
          ('a', blob_a.id, 0100644),
          ('ad/b', blob_b.id, 0100644),
          ('ad/bd/c', blob_c.id, 0100755),
          ]
        tree_id = commit_tree(self.store, blobs)
        tree = self.store[tree_id]
        tree_ad = self.store[tree['ad'][1]]
        tree_bd = self.store[tree_ad['bd'][1]]

        expected = [
          TreeEntry('', 0040000, tree_id),
          TreeEntry('a', 0100644, blob_a.id),
          TreeEntry('ad', 0040000, tree_ad.id),
          TreeEntry('ad/b', 0100644, blob_b.id),
          TreeEntry('ad/bd', 0040000, tree_bd.id),
          TreeEntry('ad/bd/c', 0100755, blob_c.id),
          ]
        actual = self.store.iter_tree_contents(tree_id, include_trees=True)
        self.assertEqual(expected, list(actual))

    def make_tag(self, name, obj):
        tag = make_object(Tag, name=name, message='',
                          tag_time=12345, tag_timezone=0,
                          tagger='Test Tagger <test@example.com>',
                          object=(object_class(obj.type_name), obj.id))
        self.store.add_object(tag)
        return tag

    def test_peel_sha(self):
        self.store.add_object(testobject)
        tag1 = self.make_tag('1', testobject)
        tag2 = self.make_tag('2', testobject)
        tag3 = self.make_tag('3', testobject)
        for obj in [testobject, tag1, tag2, tag3]:
            self.assertEqual(testobject, self.store.peel_sha(obj.id))

    def test_get_raw(self):
        self.store.add_object(testobject)
        self.assertEqual((Blob.type_num, 'yummy data'),
                         self.store.get_raw(testobject.id))

    def test_close(self):
        # For now, just check that close doesn't barf.
        self.store.add_object(testobject)
        self.store.close()


class MemoryObjectStoreTests(ObjectStoreTests, TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.store = MemoryObjectStore()

    def test_add_pack(self):
        o = MemoryObjectStore()
        f, commit, abort = o.add_pack()
        try:
            b = make_object(Blob, data="more yummy data")
            write_pack_objects(f, [(b, None)])
        except:
            abort()
            raise
        else:
            commit()

    def test_add_thin_pack(self):
        o = MemoryObjectStore()
        blob = make_object(Blob, data='yummy data')
        o.add_object(blob)

        f = StringIO()
        entries = build_pack(f, [
          (REF_DELTA, (blob.id, 'more yummy data')),
          ], store=o)
        o.add_thin_pack(f.read, None)
        packed_blob_sha = sha_to_hex(entries[0][3])
        self.assertEqual((Blob.type_num, 'more yummy data'),
                         o.get_raw(packed_blob_sha))


class PackBasedObjectStoreTests(ObjectStoreTests):

    def tearDown(self):
        for pack in self.store.packs:
            pack.close()

    def test_empty_packs(self):
        self.assertEqual([], self.store.packs)

    def test_pack_loose_objects(self):
        b1 = make_object(Blob, data="yummy data")
        self.store.add_object(b1)
        b2 = make_object(Blob, data="more yummy data")
        self.store.add_object(b2)
        self.assertEqual([], self.store.packs)
        self.assertEqual(2, self.store.pack_loose_objects())
        self.assertNotEquals([], self.store.packs)
        self.assertEqual(0, self.store.pack_loose_objects())


class DiskObjectStoreTests(PackBasedObjectStoreTests, TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.store_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.store_dir)
        self.store = DiskObjectStore.init(self.store_dir)

    def tearDown(self):
        TestCase.tearDown(self)
        PackBasedObjectStoreTests.tearDown(self)

    def test_alternates(self):
        alternate_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, alternate_dir)
        alternate_store = DiskObjectStore(alternate_dir)
        b2 = make_object(Blob, data="yummy data")
        alternate_store.add_object(b2)
        store = DiskObjectStore(self.store_dir)
        self.assertRaises(KeyError, store.__getitem__, b2.id)
        store.add_alternate_path(alternate_dir)
        self.assertIn(b2.id, store)
        self.assertEqual(b2, store[b2.id])

    def test_add_alternate_path(self):
        store = DiskObjectStore(self.store_dir)
        self.assertEqual([], store._read_alternate_paths())
        store.add_alternate_path("/foo/path")
        self.assertEqual(["/foo/path"], store._read_alternate_paths())
        store.add_alternate_path("/bar/path")
        self.assertEqual(
            ["/foo/path", "/bar/path"],
            store._read_alternate_paths())

    def test_rel_alternative_path(self):
        alternate_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, alternate_dir)
        alternate_store = DiskObjectStore(alternate_dir)
        b2 = make_object(Blob, data="yummy data")
        alternate_store.add_object(b2)
        store = DiskObjectStore(self.store_dir)
        self.assertRaises(KeyError, store.__getitem__, b2.id)
        store.add_alternate_path(os.path.relpath(alternate_dir, self.store_dir))
        self.assertEqual(list(alternate_store), list(store.alternates[0]))
        self.assertIn(b2.id, store)
        self.assertEqual(b2, store[b2.id])

    def test_pack_dir(self):
        o = DiskObjectStore(self.store_dir)
        self.assertEqual(os.path.join(self.store_dir, "pack"), o.pack_dir)

    def test_add_pack(self):
        o = DiskObjectStore(self.store_dir)
        f, commit, abort = o.add_pack()
        try:
            b = make_object(Blob, data="more yummy data")
            write_pack_objects(f, [(b, None)])
        except:
            abort()
            raise
        else:
            commit()

    def test_add_thin_pack(self):
        o = DiskObjectStore(self.store_dir)
        blob = make_object(Blob, data='yummy data')
        o.add_object(blob)

        f = StringIO()
        entries = build_pack(f, [
          (REF_DELTA, (blob.id, 'more yummy data')),
          ], store=o)
        pack = o.add_thin_pack(f.read, None)
        try:
            packed_blob_sha = sha_to_hex(entries[0][3])
            pack.check_length_and_checksum()
            self.assertEqual(sorted([blob.id, packed_blob_sha]), list(pack))
            self.assertTrue(o.contains_packed(packed_blob_sha))
            self.assertTrue(o.contains_packed(blob.id))
            self.assertEqual((Blob.type_num, 'more yummy data'),
                             o.get_raw(packed_blob_sha))
        finally:
            # FIXME: DiskObjectStore should have close() which do the following:
            for p in o._pack_cache or []:
                p.close()

            pack.close()

class TreeLookupPathTests(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.store = MemoryObjectStore()
        blob_a = make_object(Blob, data='a')
        blob_b = make_object(Blob, data='b')
        blob_c = make_object(Blob, data='c')
        for blob in [blob_a, blob_b, blob_c]:
            self.store.add_object(blob)

        blobs = [
          ('a', blob_a.id, 0100644),
          ('ad/b', blob_b.id, 0100644),
          ('ad/bd/c', blob_c.id, 0100755),
          ('ad/c', blob_c.id, 0100644),
          ('c', blob_c.id, 0100644),
          ]
        self.tree_id = commit_tree(self.store, blobs)

    def get_object(self, sha):
        return self.store[sha]

    def test_lookup_blob(self):
        o_id = tree_lookup_path(self.get_object, self.tree_id, 'a')[1]
        self.assertTrue(isinstance(self.store[o_id], Blob))

    def test_lookup_tree(self):
        o_id = tree_lookup_path(self.get_object, self.tree_id, 'ad')[1]
        self.assertTrue(isinstance(self.store[o_id], Tree))
        o_id = tree_lookup_path(self.get_object, self.tree_id, 'ad/bd')[1]
        self.assertTrue(isinstance(self.store[o_id], Tree))
        o_id = tree_lookup_path(self.get_object, self.tree_id, 'ad/bd/')[1]
        self.assertTrue(isinstance(self.store[o_id], Tree))

    def test_lookup_nonexistent(self):
        self.assertRaises(KeyError, tree_lookup_path, self.get_object, self.tree_id, 'j')

    def test_lookup_not_tree(self):
        self.assertRaises(NotTreeError, tree_lookup_path, self.get_object, self.tree_id, 'ad/b/j')

# TODO: MissingObjectFinderTests

class ObjectStoreGraphWalkerTests(TestCase):

    def get_walker(self, heads, parent_map):
        return ObjectStoreGraphWalker(heads,
            parent_map.__getitem__)

    def test_empty(self):
        gw = self.get_walker([], {})
        self.assertIs(None, gw.next())
        gw.ack("aa" * 20)
        self.assertIs(None, gw.next())

    def test_descends(self):
        gw = self.get_walker(["a"], {"a": ["b"], "b": []})
        self.assertEqual("a", gw.next())
        self.assertEqual("b", gw.next())

    def test_present(self):
        gw = self.get_walker(["a"], {"a": ["b"], "b": []})
        gw.ack("a")
        self.assertIs(None, gw.next())

    def test_parent_present(self):
        gw = self.get_walker(["a"], {"a": ["b"], "b": []})
        self.assertEqual("a", gw.next())
        gw.ack("a")
        self.assertIs(None, gw.next())

    def test_child_ack_later(self):
        gw = self.get_walker(["a"], {"a": ["b"], "b": ["c"], "c": []})
        self.assertEqual("a", gw.next())
        self.assertEqual("b", gw.next())
        gw.ack("a")
        self.assertIs(None, gw.next())

    def test_only_once(self):
        # a  b
        # |  |
        # c  d
        # \ /
        #  e
        gw = self.get_walker(["a", "b"], {
                "a": ["c"],
                "b": ["d"],
                "c": ["e"],
                "d": ["e"],
                "e": [],
                })
        self.assertEqual("a", gw.next())
        self.assertEqual("c", gw.next())
        gw.ack("a")
        self.assertEqual("b", gw.next())
        self.assertEqual("d", gw.next())
        self.assertIs(None, gw.next())

########NEW FILE########
__FILENAME__ = test_pack
# test_pack.py -- Tests for the handling of git packs.
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2008 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License, or (at your option) any later version of the license.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for Dulwich packs."""


from cStringIO import StringIO
import os
import shutil
import tempfile
import zlib

from dulwich._compat import (
    make_sha,
    )
from dulwich.errors import (
    ChecksumMismatch,
    )
from dulwich.file import (
    GitFile,
    )
from dulwich.object_store import (
    MemoryObjectStore,
    )
from dulwich.objects import (
    Blob,
    hex_to_sha,
    sha_to_hex,
    Commit,
    Tree,
    Blob,
    )
from dulwich.pack import (
    OFS_DELTA,
    REF_DELTA,
    DELTA_TYPES,
    MemoryPackIndex,
    Pack,
    PackData,
    apply_delta,
    create_delta,
    deltify_pack_objects,
    load_pack_index,
    UnpackedObject,
    read_zlib_chunks,
    write_pack_header,
    write_pack_index_v1,
    write_pack_index_v2,
    SHA1Writer,
    write_pack_object,
    write_pack,
    unpack_object,
    compute_file_sha,
    PackStreamReader,
    DeltaChainIterator,
    )
from dulwich.tests import (
    TestCase,
    )
from utils import (
    make_object,
    build_pack,
    )

pack1_sha = 'bc63ddad95e7321ee734ea11a7a62d314e0d7481'

a_sha = '6f670c0fb53f9463760b7295fbb814e965fb20c8'
tree_sha = 'b2a2766a2879c209ab1176e7e778b81ae422eeaa'
commit_sha = 'f18faa16531ac570a3fdc8c7ca16682548dafd12'


class PackTests(TestCase):
    """Base class for testing packs"""

    def setUp(self):
        super(PackTests, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)

    datadir = os.path.abspath(os.path.join(os.path.dirname(__file__),
        'data/packs'))

    def get_pack_index(self, sha):
        """Returns a PackIndex from the datadir with the given sha"""
        return load_pack_index(os.path.join(self.datadir, 'pack-%s.idx' % sha))

    def get_pack_data(self, sha):
        """Returns a PackData object from the datadir with the given sha"""
        return PackData(os.path.join(self.datadir, 'pack-%s.pack' % sha))

    def get_pack(self, sha):
        return Pack(os.path.join(self.datadir, 'pack-%s' % sha))

    def assertSucceeds(self, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except ChecksumMismatch, e:
            self.fail(e)


class PackIndexTests(PackTests):
    """Class that tests the index of packfiles"""

    def test_object_index(self):
        """Tests that the correct object offset is returned from the index."""
        p = self.get_pack_index(pack1_sha)
        self.assertRaises(KeyError, p.object_index, pack1_sha)
        self.assertEqual(p.object_index(a_sha), 178)
        self.assertEqual(p.object_index(tree_sha), 138)
        self.assertEqual(p.object_index(commit_sha), 12)

    def test_index_len(self):
        p = self.get_pack_index(pack1_sha)
        self.assertEqual(3, len(p))

    def test_get_stored_checksum(self):
        p = self.get_pack_index(pack1_sha)
        self.assertEqual('f2848e2ad16f329ae1c92e3b95e91888daa5bd01',
                          sha_to_hex(p.get_stored_checksum()))
        self.assertEqual('721980e866af9a5f93ad674144e1459b8ba3e7b7',
                          sha_to_hex(p.get_pack_checksum()))

    def test_index_check(self):
        p = self.get_pack_index(pack1_sha)
        self.assertSucceeds(p.check)

    def test_iterentries(self):
        p = self.get_pack_index(pack1_sha)
        entries = [(sha_to_hex(s), o, c) for s, o, c in p.iterentries()]
        self.assertEqual([
          ('6f670c0fb53f9463760b7295fbb814e965fb20c8', 178, None),
          ('b2a2766a2879c209ab1176e7e778b81ae422eeaa', 138, None),
          ('f18faa16531ac570a3fdc8c7ca16682548dafd12', 12, None)
          ], entries)

    def test_iter(self):
        p = self.get_pack_index(pack1_sha)
        self.assertEqual(set([tree_sha, commit_sha, a_sha]), set(p))


class TestPackDeltas(TestCase):

    test_string1 = 'The answer was flailing in the wind'
    test_string2 = 'The answer was falling down the pipe'
    test_string3 = 'zzzzz'

    test_string_empty = ''
    test_string_big = 'Z' * 8192
    test_string_huge = 'Z' * 100000

    def _test_roundtrip(self, base, target):
        self.assertEqual(target,
                          ''.join(apply_delta(base, create_delta(base, target))))

    def test_nochange(self):
        self._test_roundtrip(self.test_string1, self.test_string1)

    def test_change(self):
        self._test_roundtrip(self.test_string1, self.test_string2)

    def test_rewrite(self):
        self._test_roundtrip(self.test_string1, self.test_string3)

    def test_overflow(self):
        self._test_roundtrip(self.test_string_empty, self.test_string_big)

    def test_overflow_64k(self):
        self.skipTest("big strings don't work yet")
        self._test_roundtrip(self.test_string_huge, self.test_string_huge)


class TestPackData(PackTests):
    """Tests getting the data from the packfile."""

    def test_create_pack(self):
        p = self.get_pack_data(pack1_sha)

    def test_from_file(self):
        path = os.path.join(self.datadir, 'pack-%s.pack' % pack1_sha)
        PackData.from_file(open(path), os.path.getsize(path))

    def test_pack_len(self):
        p = self.get_pack_data(pack1_sha)
        self.assertEqual(3, len(p))

    def test_index_check(self):
        p = self.get_pack_data(pack1_sha)
        self.assertSucceeds(p.check)

    def test_iterobjects(self):
        p = self.get_pack_data(pack1_sha)
        commit_data = ('tree b2a2766a2879c209ab1176e7e778b81ae422eeaa\n'
                       'author James Westby <jw+debian@jameswestby.net> '
                       '1174945067 +0100\n'
                       'committer James Westby <jw+debian@jameswestby.net> '
                       '1174945067 +0100\n'
                       '\n'
                       'Test commit\n')
        blob_sha = '6f670c0fb53f9463760b7295fbb814e965fb20c8'
        tree_data = '100644 a\0%s' % hex_to_sha(blob_sha)
        actual = []
        for offset, type_num, chunks, crc32 in p.iterobjects():
            actual.append((offset, type_num, ''.join(chunks), crc32))
        self.assertEqual([
          (12, 1, commit_data, 3775879613L),
          (138, 2, tree_data, 912998690L),
          (178, 3, 'test 1\n', 1373561701L)
          ], actual)

    def test_iterentries(self):
        p = self.get_pack_data(pack1_sha)
        entries = set((sha_to_hex(s), o, c) for s, o, c in p.iterentries())
        self.assertEqual(set([
          ('6f670c0fb53f9463760b7295fbb814e965fb20c8', 178, 1373561701L),
          ('b2a2766a2879c209ab1176e7e778b81ae422eeaa', 138, 912998690L),
          ('f18faa16531ac570a3fdc8c7ca16682548dafd12', 12, 3775879613L),
          ]), entries)

    def test_create_index_v1(self):
        p = self.get_pack_data(pack1_sha)
        filename = os.path.join(self.tempdir, 'v1test.idx')
        p.create_index_v1(filename)
        idx1 = load_pack_index(filename)
        idx2 = self.get_pack_index(pack1_sha)
        self.assertEqual(idx1, idx2)

    def test_create_index_v2(self):
        p = self.get_pack_data(pack1_sha)
        filename = os.path.join(self.tempdir, 'v2test.idx')
        p.create_index_v2(filename)
        idx1 = load_pack_index(filename)
        idx2 = self.get_pack_index(pack1_sha)
        self.assertEqual(idx1, idx2)

    def test_compute_file_sha(self):
        f = StringIO('abcd1234wxyz')
        self.assertEqual(make_sha('abcd1234wxyz').hexdigest(),
                         compute_file_sha(f).hexdigest())
        self.assertEqual(make_sha('abcd1234wxyz').hexdigest(),
                         compute_file_sha(f, buffer_size=5).hexdigest())
        self.assertEqual(make_sha('abcd1234').hexdigest(),
                         compute_file_sha(f, end_ofs=-4).hexdigest())
        self.assertEqual(make_sha('1234wxyz').hexdigest(),
                         compute_file_sha(f, start_ofs=4).hexdigest())
        self.assertEqual(
          make_sha('1234').hexdigest(),
          compute_file_sha(f, start_ofs=4, end_ofs=-4).hexdigest())


class TestPack(PackTests):

    def test_len(self):
        p = self.get_pack(pack1_sha)
        self.assertEqual(3, len(p))

    def test_contains(self):
        p = self.get_pack(pack1_sha)
        self.assertTrue(tree_sha in p)

    def test_get(self):
        p = self.get_pack(pack1_sha)
        self.assertEqual(type(p[tree_sha]), Tree)

    def test_iter(self):
        p = self.get_pack(pack1_sha)
        self.assertEqual(set([tree_sha, commit_sha, a_sha]), set(p))

    def test_iterobjects(self):
        p = self.get_pack(pack1_sha)
        expected = set([p[s] for s in [commit_sha, tree_sha, a_sha]])
        self.assertEqual(expected, set(list(p.iterobjects())))

    def test_pack_tuples(self):
        p = self.get_pack(pack1_sha)
        tuples = p.pack_tuples()
        expected = set([(p[s], None) for s in [commit_sha, tree_sha, a_sha]])
        self.assertEqual(expected, set(list(tuples)))
        self.assertEqual(expected, set(list(tuples)))
        self.assertEqual(3, len(tuples))

    def test_get_object_at(self):
        """Tests random access for non-delta objects"""
        p = self.get_pack(pack1_sha)
        obj = p[a_sha]
        self.assertEqual(obj.type_name, 'blob')
        self.assertEqual(obj.sha().hexdigest(), a_sha)
        obj = p[tree_sha]
        self.assertEqual(obj.type_name, 'tree')
        self.assertEqual(obj.sha().hexdigest(), tree_sha)
        obj = p[commit_sha]
        self.assertEqual(obj.type_name, 'commit')
        self.assertEqual(obj.sha().hexdigest(), commit_sha)

    def test_copy(self):
        origpack = self.get_pack(pack1_sha)

        try:
            self.assertSucceeds(origpack.index.check)
            basename = os.path.join(self.tempdir, 'Elch')
            write_pack(basename, origpack.pack_tuples())
            newpack = Pack(basename)

            try:
                self.assertEqual(origpack, newpack)
                self.assertSucceeds(newpack.index.check)
                self.assertEqual(origpack.name(), newpack.name())
                self.assertEqual(origpack.index.get_pack_checksum(),
                                  newpack.index.get_pack_checksum())

                wrong_version = origpack.index.version != newpack.index.version
                orig_checksum = origpack.index.get_stored_checksum()
                new_checksum = newpack.index.get_stored_checksum()
                self.assertTrue(wrong_version or orig_checksum == new_checksum)
            finally:
                newpack.close()
        finally:
            origpack.close()

    def test_commit_obj(self):
        p = self.get_pack(pack1_sha)
        commit = p[commit_sha]
        self.assertEqual('James Westby <jw+debian@jameswestby.net>',
                          commit.author)
        self.assertEqual([], commit.parents)

    def _copy_pack(self, origpack):
        basename = os.path.join(self.tempdir, 'somepack')
        write_pack(basename, origpack.pack_tuples())
        return Pack(basename)

    def test_keep_no_message(self):
        p = self.get_pack(pack1_sha)
        p = self._copy_pack(p)

        keepfile_name = p.keep()
        # file should exist
        self.assertTrue(os.path.exists(keepfile_name))

        f = open(keepfile_name, 'r')
        try:
            buf = f.read()
            self.assertEqual('', buf)
        finally:
            f.close()

    def test_keep_message(self):
        p = self.get_pack(pack1_sha)
        p = self._copy_pack(p)

        msg = 'some message'
        keepfile_name = p.keep(msg)

        # file should exist
        self.assertTrue(os.path.exists(keepfile_name))

        # and contain the right message, with a linefeed
        f = open(keepfile_name, 'r')
        try:
            buf = f.read()
            self.assertEqual(msg + '\n', buf)
        finally:
            f.close()

    def test_name(self):
        p = self.get_pack(pack1_sha)
        self.assertEqual(pack1_sha, p.name())

    def test_length_mismatch(self):
        data = self.get_pack_data(pack1_sha)
        index = self.get_pack_index(pack1_sha)
        Pack.from_objects(data, index).check_length_and_checksum()

        data._file.seek(12)
        bad_file = StringIO()
        write_pack_header(bad_file, 9999)
        bad_file.write(data._file.read())
        bad_file = StringIO(bad_file.getvalue())
        bad_data = PackData('', file=bad_file)
        bad_pack = Pack.from_lazy_objects(lambda: bad_data, lambda: index)
        self.assertRaises(AssertionError, lambda: bad_pack.data)
        self.assertRaises(AssertionError,
                          lambda: bad_pack.check_length_and_checksum())

    def test_checksum_mismatch(self):
        data = self.get_pack_data(pack1_sha)
        index = self.get_pack_index(pack1_sha)
        Pack.from_objects(data, index).check_length_and_checksum()

        data._file.seek(0)
        bad_file = StringIO(data._file.read()[:-20] + ('\xff' * 20))
        bad_data = PackData('', file=bad_file)
        bad_pack = Pack.from_lazy_objects(lambda: bad_data, lambda: index)
        self.assertRaises(ChecksumMismatch, lambda: bad_pack.data)
        self.assertRaises(ChecksumMismatch, lambda:
                          bad_pack.check_length_and_checksum())

    def test_iterobjects(self):
        p = self.get_pack(pack1_sha)
        objs = dict((o.id, o) for o in p.iterobjects())
        self.assertEqual(3, len(objs))
        self.assertEqual(sorted(objs), sorted(p.index))
        self.assertTrue(isinstance(objs[a_sha], Blob))
        self.assertTrue(isinstance(objs[tree_sha], Tree))
        self.assertTrue(isinstance(objs[commit_sha], Commit))


class TestThinPack(PackTests):

    def setUp(self):
        super(TestThinPack, self).setUp()
        self.store = MemoryObjectStore()
        self.blobs = {}
        for blob in ('foo', 'bar', 'foo1234', 'bar2468'):
            self.blobs[blob] = make_object(Blob, data=blob)
        self.store.add_object(self.blobs['foo'])
        self.store.add_object(self.blobs['bar'])

        # Build a thin pack. 'foo' is as an external reference, 'bar' an
        # internal reference.
        self.pack_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.pack_dir)
        self.pack_prefix = os.path.join(self.pack_dir, 'pack')
        with open(self.pack_prefix + '.pack', 'wb') as f:
            build_pack(f, [
                (REF_DELTA, (self.blobs['foo'].id, 'foo1234')),
                (Blob.type_num, 'bar'),
                (REF_DELTA, (self.blobs['bar'].id, 'bar2468'))],
                store=self.store)

        # Index the new pack.
        pack = self.make_pack(True)
        data = PackData(pack._data_path)
        data.pack = pack
        data.create_index(self.pack_prefix + '.idx')

        del self.store[self.blobs['bar'].id]

    def make_pack(self, resolve_ext_ref):
        return Pack(
            self.pack_prefix,
            resolve_ext_ref=self.store.get_raw if resolve_ext_ref else None)

    def test_get_raw(self):
        self.assertRaises(
            KeyError, self.make_pack(False).get_raw, self.blobs['foo1234'].id)
        self.assertEqual(
            (3, 'foo1234'),
            self.make_pack(True).get_raw(self.blobs['foo1234'].id))

    def test_iterobjects(self):
        self.assertRaises(KeyError, list, self.make_pack(False).iterobjects())
        self.assertEqual(
            sorted([self.blobs['foo1234'].id, self.blobs['bar'].id,
                    self.blobs['bar2468'].id]),
            sorted(o.id for o in self.make_pack(True).iterobjects()))


class WritePackTests(TestCase):

    def test_write_pack_header(self):
        f = StringIO()
        write_pack_header(f, 42)
        self.assertEqual('PACK\x00\x00\x00\x02\x00\x00\x00*',
                f.getvalue())

    def test_write_pack_object(self):
        f = StringIO()
        f.write('header')
        offset = f.tell()
        crc32 = write_pack_object(f, Blob.type_num, 'blob')
        self.assertEqual(crc32, zlib.crc32(f.getvalue()[6:]) & 0xffffffff)

        f.write('x')  # unpack_object needs extra trailing data.
        f.seek(offset)
        comp_len = len(f.getvalue()) - offset - 1
        unpacked, unused = unpack_object(f.read, compute_crc32=True)
        self.assertEqual(Blob.type_num, unpacked.pack_type_num)
        self.assertEqual(Blob.type_num, unpacked.obj_type_num)
        self.assertEqual(['blob'], unpacked.decomp_chunks)
        self.assertEqual(crc32, unpacked.crc32)
        self.assertEqual('x', unused)

    def test_write_pack_object_sha(self):
        f = StringIO()
        f.write('header')
        offset = f.tell()
        sha_a = make_sha('foo')
        sha_b = sha_a.copy()
        write_pack_object(f, Blob.type_num, 'blob', sha=sha_a)
        self.assertNotEqual(sha_a.digest(), sha_b.digest())
        sha_b.update(f.getvalue()[offset:])
        self.assertEqual(sha_a.digest(), sha_b.digest())


pack_checksum = hex_to_sha('721980e866af9a5f93ad674144e1459b8ba3e7b7')


class BaseTestPackIndexWriting(object):

    def assertSucceeds(self, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except ChecksumMismatch, e:
            self.fail(e)

    def index(self, filename, entries, pack_checksum):
        raise NotImplementedError(self.index)

    def test_empty(self):
        idx = self.index('empty.idx', [], pack_checksum)
        self.assertEqual(idx.get_pack_checksum(), pack_checksum)
        self.assertEqual(0, len(idx))

    def test_large(self):
        entry1_sha = hex_to_sha('4e6388232ec39792661e2e75db8fb117fc869ce6')
        entry2_sha = hex_to_sha('e98f071751bd77f59967bfa671cd2caebdccc9a2')
        entries = [(entry1_sha, 0xf2972d0830529b87, 24),
                   (entry2_sha, (~0xf2972d0830529b87)&(2**64-1), 92)]
        if not self._supports_large:
            self.assertRaises(TypeError, self.index, 'single.idx',
                entries, pack_checksum)
            return
        idx = self.index('single.idx', entries, pack_checksum)
        self.assertEqual(idx.get_pack_checksum(), pack_checksum)
        self.assertEqual(2, len(idx))
        actual_entries = list(idx.iterentries())
        self.assertEqual(len(entries), len(actual_entries))
        for mine, actual in zip(entries, actual_entries):
            my_sha, my_offset, my_crc = mine
            actual_sha, actual_offset, actual_crc = actual
            self.assertEqual(my_sha, actual_sha)
            self.assertEqual(my_offset, actual_offset)
            if self._has_crc32_checksum:
                self.assertEqual(my_crc, actual_crc)
            else:
                self.assertTrue(actual_crc is None)

    def test_single(self):
        entry_sha = hex_to_sha('6f670c0fb53f9463760b7295fbb814e965fb20c8')
        my_entries = [(entry_sha, 178, 42)]
        idx = self.index('single.idx', my_entries, pack_checksum)
        self.assertEqual(idx.get_pack_checksum(), pack_checksum)
        self.assertEqual(1, len(idx))
        actual_entries = list(idx.iterentries())
        self.assertEqual(len(my_entries), len(actual_entries))
        for mine, actual in zip(my_entries, actual_entries):
            my_sha, my_offset, my_crc = mine
            actual_sha, actual_offset, actual_crc = actual
            self.assertEqual(my_sha, actual_sha)
            self.assertEqual(my_offset, actual_offset)
            if self._has_crc32_checksum:
                self.assertEqual(my_crc, actual_crc)
            else:
                self.assertTrue(actual_crc is None)


class BaseTestFilePackIndexWriting(BaseTestPackIndexWriting):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def index(self, filename, entries, pack_checksum):
        path = os.path.join(self.tempdir, filename)
        self.writeIndex(path, entries, pack_checksum)
        idx = load_pack_index(path)
        self.assertSucceeds(idx.check)
        self.assertEqual(idx.version, self._expected_version)
        return idx

    def writeIndex(self, filename, entries, pack_checksum):
        # FIXME: Write to StringIO instead rather than hitting disk ?
        f = GitFile(filename, "wb")
        try:
            self._write_fn(f, entries, pack_checksum)
        finally:
            f.close()


class TestMemoryIndexWriting(TestCase, BaseTestPackIndexWriting):

    def setUp(self):
        TestCase.setUp(self)
        self._has_crc32_checksum = True
        self._supports_large = True

    def index(self, filename, entries, pack_checksum):
        return MemoryPackIndex(entries, pack_checksum)

    def tearDown(self):
        TestCase.tearDown(self)


class TestPackIndexWritingv1(TestCase, BaseTestFilePackIndexWriting):

    def setUp(self):
        TestCase.setUp(self)
        BaseTestFilePackIndexWriting.setUp(self)
        self._has_crc32_checksum = False
        self._expected_version = 1
        self._supports_large = False
        self._write_fn = write_pack_index_v1

    def tearDown(self):
        TestCase.tearDown(self)
        BaseTestFilePackIndexWriting.tearDown(self)


class TestPackIndexWritingv2(TestCase, BaseTestFilePackIndexWriting):

    def setUp(self):
        TestCase.setUp(self)
        BaseTestFilePackIndexWriting.setUp(self)
        self._has_crc32_checksum = True
        self._supports_large = True
        self._expected_version = 2
        self._write_fn = write_pack_index_v2

    def tearDown(self):
        TestCase.tearDown(self)
        BaseTestFilePackIndexWriting.tearDown(self)


class ReadZlibTests(TestCase):

    decomp = (
      'tree 4ada885c9196b6b6fa08744b5862bf92896fc002\n'
      'parent None\n'
      'author Jelmer Vernooij <jelmer@samba.org> 1228980214 +0000\n'
      'committer Jelmer Vernooij <jelmer@samba.org> 1228980214 +0000\n'
      '\n'
      "Provide replacement for mmap()'s offset argument.")
    comp = zlib.compress(decomp)
    extra = 'nextobject'

    def setUp(self):
        super(ReadZlibTests, self).setUp()
        self.read = StringIO(self.comp + self.extra).read
        self.unpacked = UnpackedObject(Tree.type_num, None, len(self.decomp), 0)

    def test_decompress_size(self):
        good_decomp_len = len(self.decomp)
        self.unpacked.decomp_len = -1
        self.assertRaises(ValueError, read_zlib_chunks, self.read,
                          self.unpacked)
        self.unpacked.decomp_len = good_decomp_len - 1
        self.assertRaises(zlib.error, read_zlib_chunks, self.read,
                          self.unpacked)
        self.unpacked.decomp_len = good_decomp_len + 1
        self.assertRaises(zlib.error, read_zlib_chunks, self.read,
                          self.unpacked)

    def test_decompress_truncated(self):
        read = StringIO(self.comp[:10]).read
        self.assertRaises(zlib.error, read_zlib_chunks, read, self.unpacked)

        read = StringIO(self.comp).read
        self.assertRaises(zlib.error, read_zlib_chunks, read, self.unpacked)

    def test_decompress_empty(self):
        unpacked = UnpackedObject(Tree.type_num, None, 0, None)
        comp = zlib.compress('')
        read = StringIO(comp + self.extra).read
        unused = read_zlib_chunks(read, unpacked)
        self.assertEqual('', ''.join(unpacked.decomp_chunks))
        self.assertNotEquals('', unused)
        self.assertEqual(self.extra, unused + read())

    def test_decompress_no_crc32(self):
        self.unpacked.crc32 = None
        read_zlib_chunks(self.read, self.unpacked)
        self.assertEqual(None, self.unpacked.crc32)

    def _do_decompress_test(self, buffer_size, **kwargs):
        unused = read_zlib_chunks(self.read, self.unpacked,
                                  buffer_size=buffer_size, **kwargs)
        self.assertEqual(self.decomp, ''.join(self.unpacked.decomp_chunks))
        self.assertEqual(zlib.crc32(self.comp), self.unpacked.crc32)
        self.assertNotEquals('', unused)
        self.assertEqual(self.extra, unused + self.read())

    def test_simple_decompress(self):
        self._do_decompress_test(4096)
        self.assertEqual(None, self.unpacked.comp_chunks)

    # These buffer sizes are not intended to be realistic, but rather simulate
    # larger buffer sizes that may end at various places.
    def test_decompress_buffer_size_1(self):
        self._do_decompress_test(1)

    def test_decompress_buffer_size_2(self):
        self._do_decompress_test(2)

    def test_decompress_buffer_size_3(self):
        self._do_decompress_test(3)

    def test_decompress_buffer_size_4(self):
        self._do_decompress_test(4)

    def test_decompress_include_comp(self):
        self._do_decompress_test(4096, include_comp=True)
        self.assertEqual(self.comp, ''.join(self.unpacked.comp_chunks))


class DeltifyTests(TestCase):

    def test_empty(self):
        self.assertEqual([], list(deltify_pack_objects([])))

    def test_single(self):
        b = Blob.from_string("foo")
        self.assertEqual(
            [(b.type_num, b.sha().digest(), None, b.as_raw_string())],
            list(deltify_pack_objects([(b, "")])))

    def test_simple_delta(self):
        b1 = Blob.from_string("a" * 101)
        b2 = Blob.from_string("a" * 100)
        delta = create_delta(b1.as_raw_string(), b2.as_raw_string())
        self.assertEqual([
            (b1.type_num, b1.sha().digest(), None, b1.as_raw_string()),
            (b2.type_num, b2.sha().digest(), b1.sha().digest(), delta)
            ],
            list(deltify_pack_objects([(b1, ""), (b2, "")])))


class TestPackStreamReader(TestCase):

    def test_read_objects_emtpy(self):
        f = StringIO()
        build_pack(f, [])
        reader = PackStreamReader(f.read)
        self.assertEqual(0, len(list(reader.read_objects())))

    def test_read_objects(self):
        f = StringIO()
        entries = build_pack(f, [
          (Blob.type_num, 'blob'),
          (OFS_DELTA, (0, 'blob1')),
          ])
        reader = PackStreamReader(f.read)
        objects = list(reader.read_objects(compute_crc32=True))
        self.assertEqual(2, len(objects))

        unpacked_blob, unpacked_delta = objects

        self.assertEqual(entries[0][0], unpacked_blob.offset)
        self.assertEqual(Blob.type_num, unpacked_blob.pack_type_num)
        self.assertEqual(Blob.type_num, unpacked_blob.obj_type_num)
        self.assertEqual(None, unpacked_blob.delta_base)
        self.assertEqual('blob', ''.join(unpacked_blob.decomp_chunks))
        self.assertEqual(entries[0][4], unpacked_blob.crc32)

        self.assertEqual(entries[1][0], unpacked_delta.offset)
        self.assertEqual(OFS_DELTA, unpacked_delta.pack_type_num)
        self.assertEqual(None, unpacked_delta.obj_type_num)
        self.assertEqual(unpacked_delta.offset - unpacked_blob.offset,
                         unpacked_delta.delta_base)
        delta = create_delta('blob', 'blob1')
        self.assertEqual(delta, ''.join(unpacked_delta.decomp_chunks))
        self.assertEqual(entries[1][4], unpacked_delta.crc32)

    def test_read_objects_buffered(self):
        f = StringIO()
        build_pack(f, [
          (Blob.type_num, 'blob'),
          (OFS_DELTA, (0, 'blob1')),
          ])
        reader = PackStreamReader(f.read, zlib_bufsize=4)
        self.assertEqual(2, len(list(reader.read_objects())))

    def test_read_objects_empty(self):
        reader = PackStreamReader(StringIO().read)
        self.assertEqual([], list(reader.read_objects()))


class TestPackIterator(DeltaChainIterator):

    _compute_crc32 = True

    def __init__(self, *args, **kwargs):
        super(TestPackIterator, self).__init__(*args, **kwargs)
        self._unpacked_offsets = set()

    def _result(self, unpacked):
        """Return entries in the same format as build_pack."""
        return (unpacked.offset, unpacked.obj_type_num,
                ''.join(unpacked.obj_chunks), unpacked.sha(), unpacked.crc32)

    def _resolve_object(self, offset, pack_type_num, base_chunks):
        assert offset not in self._unpacked_offsets, (
                'Attempted to re-inflate offset %i' % offset)
        self._unpacked_offsets.add(offset)
        return super(TestPackIterator, self)._resolve_object(
          offset, pack_type_num, base_chunks)


class DeltaChainIteratorTests(TestCase):

    def setUp(self):
        super(DeltaChainIteratorTests, self).setUp()
        self.store = MemoryObjectStore()
        self.fetched = set()

    def store_blobs(self, blobs_data):
        blobs = []
        for data in blobs_data:
            blob = make_object(Blob, data=data)
            blobs.append(blob)
            self.store.add_object(blob)
        return blobs

    def get_raw_no_repeat(self, bin_sha):
        """Wrapper around store.get_raw that doesn't allow repeat lookups."""
        hex_sha = sha_to_hex(bin_sha)
        self.assertFalse(hex_sha in self.fetched,
                         'Attempted to re-fetch object %s' % hex_sha)
        self.fetched.add(hex_sha)
        return self.store.get_raw(hex_sha)

    def make_pack_iter(self, f, thin=None):
        if thin is None:
            thin = bool(list(self.store))
        resolve_ext_ref = thin and self.get_raw_no_repeat or None
        data = PackData('test.pack', file=f)
        return TestPackIterator.for_pack_data(
          data, resolve_ext_ref=resolve_ext_ref)

    def assertEntriesMatch(self, expected_indexes, entries, pack_iter):
        expected = [entries[i] for i in expected_indexes]
        self.assertEqual(expected, list(pack_iter._walk_all_chains()))

    def test_no_deltas(self):
        f = StringIO()
        entries = build_pack(f, [
          (Commit.type_num, 'commit'),
          (Blob.type_num, 'blob'),
          (Tree.type_num, 'tree'),
          ])
        self.assertEntriesMatch([0, 1, 2], entries, self.make_pack_iter(f))

    def test_ofs_deltas(self):
        f = StringIO()
        entries = build_pack(f, [
          (Blob.type_num, 'blob'),
          (OFS_DELTA, (0, 'blob1')),
          (OFS_DELTA, (0, 'blob2')),
          ])
        self.assertEntriesMatch([0, 1, 2], entries, self.make_pack_iter(f))

    def test_ofs_deltas_chain(self):
        f = StringIO()
        entries = build_pack(f, [
          (Blob.type_num, 'blob'),
          (OFS_DELTA, (0, 'blob1')),
          (OFS_DELTA, (1, 'blob2')),
          ])
        self.assertEntriesMatch([0, 1, 2], entries, self.make_pack_iter(f))

    def test_ref_deltas(self):
        f = StringIO()
        entries = build_pack(f, [
          (REF_DELTA, (1, 'blob1')),
          (Blob.type_num, ('blob')),
          (REF_DELTA, (1, 'blob2')),
          ])
        self.assertEntriesMatch([1, 0, 2], entries, self.make_pack_iter(f))

    def test_ref_deltas_chain(self):
        f = StringIO()
        entries = build_pack(f, [
          (REF_DELTA, (2, 'blob1')),
          (Blob.type_num, ('blob')),
          (REF_DELTA, (1, 'blob2')),
          ])
        self.assertEntriesMatch([1, 2, 0], entries, self.make_pack_iter(f))

    def test_ofs_and_ref_deltas(self):
        # Deltas pending on this offset are popped before deltas depending on
        # this ref.
        f = StringIO()
        entries = build_pack(f, [
          (REF_DELTA, (1, 'blob1')),
          (Blob.type_num, ('blob')),
          (OFS_DELTA, (1, 'blob2')),
          ])
        self.assertEntriesMatch([1, 2, 0], entries, self.make_pack_iter(f))

    def test_mixed_chain(self):
        f = StringIO()
        entries = build_pack(f, [
          (Blob.type_num, 'blob'),
          (REF_DELTA, (2, 'blob2')),
          (OFS_DELTA, (0, 'blob1')),
          (OFS_DELTA, (1, 'blob3')),
          (OFS_DELTA, (0, 'bob')),
          ])
        self.assertEntriesMatch([0, 2, 1, 3, 4], entries,
                                self.make_pack_iter(f))

    def test_long_chain(self):
        n = 100
        objects_spec = [(Blob.type_num, 'blob')]
        for i in xrange(n):
            objects_spec.append((OFS_DELTA, (i, 'blob%i' % i)))
        f = StringIO()
        entries = build_pack(f, objects_spec)
        self.assertEntriesMatch(xrange(n + 1), entries, self.make_pack_iter(f))

    def test_branchy_chain(self):
        n = 100
        objects_spec = [(Blob.type_num, 'blob')]
        for i in xrange(n):
            objects_spec.append((OFS_DELTA, (0, 'blob%i' % i)))
        f = StringIO()
        entries = build_pack(f, objects_spec)
        self.assertEntriesMatch(xrange(n + 1), entries, self.make_pack_iter(f))

    def test_ext_ref(self):
        blob, = self.store_blobs(['blob'])
        f = StringIO()
        entries = build_pack(f, [(REF_DELTA, (blob.id, 'blob1'))],
                             store=self.store)
        pack_iter = self.make_pack_iter(f)
        self.assertEntriesMatch([0], entries, pack_iter)
        self.assertEqual([hex_to_sha(blob.id)], pack_iter.ext_refs())

    def test_ext_ref_chain(self):
        blob, = self.store_blobs(['blob'])
        f = StringIO()
        entries = build_pack(f, [
          (REF_DELTA, (1, 'blob2')),
          (REF_DELTA, (blob.id, 'blob1')),
          ], store=self.store)
        pack_iter = self.make_pack_iter(f)
        self.assertEntriesMatch([1, 0], entries, pack_iter)
        self.assertEqual([hex_to_sha(blob.id)], pack_iter.ext_refs())

    def test_ext_ref_multiple_times(self):
        blob, = self.store_blobs(['blob'])
        f = StringIO()
        entries = build_pack(f, [
          (REF_DELTA, (blob.id, 'blob1')),
          (REF_DELTA, (blob.id, 'blob2')),
          ], store=self.store)
        pack_iter = self.make_pack_iter(f)
        self.assertEntriesMatch([0, 1], entries, pack_iter)
        self.assertEqual([hex_to_sha(blob.id)], pack_iter.ext_refs())

    def test_multiple_ext_refs(self):
        b1, b2 = self.store_blobs(['foo', 'bar'])
        f = StringIO()
        entries = build_pack(f, [
          (REF_DELTA, (b1.id, 'foo1')),
          (REF_DELTA, (b2.id, 'bar2')),
          ], store=self.store)
        pack_iter = self.make_pack_iter(f)
        self.assertEntriesMatch([0, 1], entries, pack_iter)
        self.assertEqual([hex_to_sha(b1.id), hex_to_sha(b2.id)],
                         pack_iter.ext_refs())

    def test_bad_ext_ref_non_thin_pack(self):
        blob, = self.store_blobs(['blob'])
        f = StringIO()
        entries = build_pack(f, [(REF_DELTA, (blob.id, 'blob1'))],
                             store=self.store)
        pack_iter = self.make_pack_iter(f, thin=False)
        try:
            list(pack_iter._walk_all_chains())
            self.fail()
        except KeyError, e:
            self.assertEqual(([blob.id],), e.args)

    def test_bad_ext_ref_thin_pack(self):
        b1, b2, b3 = self.store_blobs(['foo', 'bar', 'baz'])
        f = StringIO()
        entries = build_pack(f, [
          (REF_DELTA, (1, 'foo99')),
          (REF_DELTA, (b1.id, 'foo1')),
          (REF_DELTA, (b2.id, 'bar2')),
          (REF_DELTA, (b3.id, 'baz3')),
          ], store=self.store)
        del self.store[b2.id]
        del self.store[b3.id]
        pack_iter = self.make_pack_iter(f)
        try:
            list(pack_iter._walk_all_chains())
            self.fail()
        except KeyError, e:
            self.assertEqual((sorted([b2.id, b3.id]),), e.args)

########NEW FILE########
__FILENAME__ = test_patch
# test_patch.py -- tests for patch.py
# Copyright (C) 2010 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for patch.py."""

from cStringIO import StringIO

from dulwich.objects import (
    Blob,
    Commit,
    S_IFGITLINK,
    Tree,
    )
from dulwich.object_store import (
    MemoryObjectStore,
    )
from dulwich.patch import (
    git_am_patch_split,
    write_blob_diff,
    write_commit_patch,
    write_object_diff,
    write_tree_diff,
    )
from dulwich.tests import (
    SkipTest,
    TestCase,
    )


class WriteCommitPatchTests(TestCase):

    def test_simple(self):
        f = StringIO()
        c = Commit()
        c.committer = c.author = "Jelmer <jelmer@samba.org>"
        c.commit_time = c.author_time = 1271350201
        c.commit_timezone = c.author_timezone = 0
        c.message = "This is the first line\nAnd this is the second line.\n"
        c.tree = Tree().id
        write_commit_patch(f, c, "CONTENTS", (1, 1), version="custom")
        f.seek(0)
        lines = f.readlines()
        self.assertTrue(lines[0].startswith("From 0b0d34d1b5b596c928adc9a727a4b9e03d025298"))
        self.assertEqual(lines[1], "From: Jelmer <jelmer@samba.org>\n")
        self.assertTrue(lines[2].startswith("Date: "))
        self.assertEqual([
            "Subject: [PATCH 1/1] This is the first line\n",
            "And this is the second line.\n",
            "\n",
            "\n",
            "---\n"], lines[3:8])
        self.assertEqual([
            "CONTENTS-- \n",
            "custom\n"], lines[-2:])
        if len(lines) >= 12:
            # diffstat may not be present
            self.assertEqual(lines[8], " 0 files changed\n")


class ReadGitAmPatch(TestCase):

    def test_extract(self):
        text = """From ff643aae102d8870cac88e8f007e70f58f3a7363 Mon Sep 17 00:00:00 2001
From: Jelmer Vernooij <jelmer@samba.org>
Date: Thu, 15 Apr 2010 15:40:28 +0200
Subject: [PATCH 1/2] Remove executable bit from prey.ico (triggers a lintian warning).

---
 pixmaps/prey.ico |  Bin 9662 -> 9662 bytes
 1 files changed, 0 insertions(+), 0 deletions(-)
 mode change 100755 => 100644 pixmaps/prey.ico

-- 
1.7.0.4
"""
        c, diff, version = git_am_patch_split(StringIO(text))
        self.assertEqual("Jelmer Vernooij <jelmer@samba.org>", c.committer)
        self.assertEqual("Jelmer Vernooij <jelmer@samba.org>", c.author)
        self.assertEqual("Remove executable bit from prey.ico "
            "(triggers a lintian warning).\n", c.message)
        self.assertEqual(""" pixmaps/prey.ico |  Bin 9662 -> 9662 bytes
 1 files changed, 0 insertions(+), 0 deletions(-)
 mode change 100755 => 100644 pixmaps/prey.ico

""", diff)
        self.assertEqual("1.7.0.4", version)

    def test_extract_spaces(self):
        text = """From ff643aae102d8870cac88e8f007e70f58f3a7363 Mon Sep 17 00:00:00 2001
From: Jelmer Vernooij <jelmer@samba.org>
Date: Thu, 15 Apr 2010 15:40:28 +0200
Subject:  [Dulwich-users] [PATCH] Added unit tests for
 dulwich.object_store.tree_lookup_path.

* dulwich/tests/test_object_store.py
  (TreeLookupPathTests): This test case contains a few tests that ensure the
   tree_lookup_path function works as expected.
---
 pixmaps/prey.ico |  Bin 9662 -> 9662 bytes
 1 files changed, 0 insertions(+), 0 deletions(-)
 mode change 100755 => 100644 pixmaps/prey.ico

-- 
1.7.0.4
"""
        c, diff, version = git_am_patch_split(StringIO(text))
        self.assertEqual('Added unit tests for dulwich.object_store.tree_lookup_path.\n\n* dulwich/tests/test_object_store.py\n  (TreeLookupPathTests): This test case contains a few tests that ensure the\n   tree_lookup_path function works as expected.\n', c.message)

    def test_extract_pseudo_from_header(self):
        text = """From ff643aae102d8870cac88e8f007e70f58f3a7363 Mon Sep 17 00:00:00 2001
From: Jelmer Vernooij <jelmer@samba.org>
Date: Thu, 15 Apr 2010 15:40:28 +0200
Subject:  [Dulwich-users] [PATCH] Added unit tests for
 dulwich.object_store.tree_lookup_path.

From: Jelmer Vernooy <jelmer@debian.org>

* dulwich/tests/test_object_store.py
  (TreeLookupPathTests): This test case contains a few tests that ensure the
   tree_lookup_path function works as expected.
---
 pixmaps/prey.ico |  Bin 9662 -> 9662 bytes
 1 files changed, 0 insertions(+), 0 deletions(-)
 mode change 100755 => 100644 pixmaps/prey.ico

-- 
1.7.0.4
"""
        c, diff, version = git_am_patch_split(StringIO(text))
        self.assertEqual("Jelmer Vernooy <jelmer@debian.org>", c.author)
        self.assertEqual('Added unit tests for dulwich.object_store.tree_lookup_path.\n\n* dulwich/tests/test_object_store.py\n  (TreeLookupPathTests): This test case contains a few tests that ensure the\n   tree_lookup_path function works as expected.\n', c.message)

    def test_extract_no_version_tail(self):
        text = """From ff643aae102d8870cac88e8f007e70f58f3a7363 Mon Sep 17 00:00:00 2001
From: Jelmer Vernooij <jelmer@samba.org>
Date: Thu, 15 Apr 2010 15:40:28 +0200
Subject:  [Dulwich-users] [PATCH] Added unit tests for
 dulwich.object_store.tree_lookup_path.

From: Jelmer Vernooy <jelmer@debian.org>

---
 pixmaps/prey.ico |  Bin 9662 -> 9662 bytes
 1 files changed, 0 insertions(+), 0 deletions(-)
 mode change 100755 => 100644 pixmaps/prey.ico

"""
        c, diff, version = git_am_patch_split(StringIO(text))
        self.assertEqual(None, version)

    def test_extract_mercurial(self):
        raise SkipTest("git_am_patch_split doesn't handle Mercurial patches properly yet")
        expected_diff = """diff --git a/dulwich/tests/test_patch.py b/dulwich/tests/test_patch.py
--- a/dulwich/tests/test_patch.py
+++ b/dulwich/tests/test_patch.py
@@ -158,7 +158,7 @@
 
 '''
         c, diff, version = git_am_patch_split(StringIO(text))
-        self.assertIs(None, version)
+        self.assertEqual(None, version)
 
 
 class DiffTests(TestCase):
"""
        text = """From dulwich-users-bounces+jelmer=samba.org@lists.launchpad.net Mon Nov 29 00:58:18 2010
Date: Sun, 28 Nov 2010 17:57:27 -0600
From: Augie Fackler <durin42@gmail.com>
To: dulwich-users <dulwich-users@lists.launchpad.net>
Subject: [Dulwich-users] [PATCH] test_patch: fix tests on Python 2.6
Content-Transfer-Encoding: 8bit

Change-Id: I5e51313d4ae3a65c3f00c665002a7489121bb0d6

%s

_______________________________________________
Mailing list: https://launchpad.net/~dulwich-users
Post to     : dulwich-users@lists.launchpad.net
Unsubscribe : https://launchpad.net/~dulwich-users
More help   : https://help.launchpad.net/ListHelp

""" % expected_diff
        c, diff, version = git_am_patch_split(StringIO(text))
        self.assertEqual(expected_diff, diff)
        self.assertEqual(None, version)


class DiffTests(TestCase):
    """Tests for write_blob_diff and write_tree_diff."""

    def test_blob_diff(self):
        f = StringIO()
        write_blob_diff(f, ("foo.txt", 0644, Blob.from_string("old\nsame\n")),
                           ("bar.txt", 0644, Blob.from_string("new\nsame\n")))
        self.assertEqual([
            "diff --git a/foo.txt b/bar.txt",
            "index 3b0f961..a116b51 644",
            "--- a/foo.txt",
            "+++ b/bar.txt",
            "@@ -1,2 +1,2 @@",
            "-old",
            "+new",
            " same"
            ], f.getvalue().splitlines())

    def test_blob_add(self):
        f = StringIO()
        write_blob_diff(f, (None, None, None),
                           ("bar.txt", 0644, Blob.from_string("new\nsame\n")))
        self.assertEqual([
            'diff --git /dev/null b/bar.txt',
             'new mode 644',
             'index 0000000..a116b51 644',
             '--- /dev/null',
             '+++ b/bar.txt',
             '@@ -1,0 +1,2 @@',
             '+new',
             '+same'
            ], f.getvalue().splitlines())

    def test_blob_remove(self):
        f = StringIO()
        write_blob_diff(f, ("bar.txt", 0644, Blob.from_string("new\nsame\n")),
                           (None, None, None))
        self.assertEqual([
            'diff --git a/bar.txt /dev/null',
            'deleted mode 644',
            'index a116b51..0000000',
            '--- a/bar.txt',
            '+++ /dev/null',
            '@@ -1,2 +1,0 @@',
            '-new',
            '-same'
            ], f.getvalue().splitlines())

    def test_tree_diff(self):
        f = StringIO()
        store = MemoryObjectStore()
        added = Blob.from_string("add\n")
        removed = Blob.from_string("removed\n")
        changed1 = Blob.from_string("unchanged\nremoved\n")
        changed2 = Blob.from_string("unchanged\nadded\n")
        unchanged = Blob.from_string("unchanged\n")
        tree1 = Tree()
        tree1.add("removed.txt", 0644, removed.id)
        tree1.add("changed.txt", 0644, changed1.id)
        tree1.add("unchanged.txt", 0644, changed1.id)
        tree2 = Tree()
        tree2.add("added.txt", 0644, added.id)
        tree2.add("changed.txt", 0644, changed2.id)
        tree2.add("unchanged.txt", 0644, changed1.id)
        store.add_objects([(o, None) for o in [
            tree1, tree2, added, removed, changed1, changed2, unchanged]])
        write_tree_diff(f, store, tree1.id, tree2.id)
        self.assertEqual([
            'diff --git /dev/null b/added.txt',
            'new mode 644',
            'index 0000000..76d4bb8 644',
            '--- /dev/null',
            '+++ b/added.txt',
            '@@ -1,0 +1,1 @@',
            '+add',
            'diff --git a/changed.txt b/changed.txt',
            'index bf84e48..1be2436 644',
            '--- a/changed.txt',
            '+++ b/changed.txt',
            '@@ -1,2 +1,2 @@',
            ' unchanged',
            '-removed',
            '+added',
            'diff --git a/removed.txt /dev/null',
            'deleted mode 644',
            'index 2c3f0b3..0000000',
            '--- a/removed.txt',
            '+++ /dev/null',
            '@@ -1,1 +1,0 @@',
            '-removed',
            ], f.getvalue().splitlines())

    def test_tree_diff_submodule(self):
        f = StringIO()
        store = MemoryObjectStore()
        tree1 = Tree()
        tree1.add("asubmodule", S_IFGITLINK,
            "06d0bdd9e2e20377b3180e4986b14c8549b393e4")
        tree2 = Tree()
        tree2.add("asubmodule", S_IFGITLINK,
            "cc975646af69f279396d4d5e1379ac6af80ee637")
        store.add_objects([(o, None) for o in [tree1, tree2]])
        write_tree_diff(f, store, tree1.id, tree2.id)
        self.assertEqual([
            'diff --git a/asubmodule b/asubmodule',
            'index 06d0bdd..cc97564 160000',
            '--- a/asubmodule',
            '+++ b/asubmodule',
            '@@ -1,1 +1,1 @@',
            '-Submodule commit 06d0bdd9e2e20377b3180e4986b14c8549b393e4',
            '+Submodule commit cc975646af69f279396d4d5e1379ac6af80ee637',
            ], f.getvalue().splitlines())

    def test_object_diff_blob(self):
        f = StringIO()
        b1 = Blob.from_string("old\nsame\n")
        b2 = Blob.from_string("new\nsame\n")
        store = MemoryObjectStore()
        store.add_objects([(b1, None), (b2, None)])
        write_object_diff(f, store, ("foo.txt", 0644, b1.id),
                                    ("bar.txt", 0644, b2.id))
        self.assertEqual([
            "diff --git a/foo.txt b/bar.txt",
            "index 3b0f961..a116b51 644",
            "--- a/foo.txt",
            "+++ b/bar.txt",
            "@@ -1,2 +1,2 @@",
            "-old",
            "+new",
            " same"
            ], f.getvalue().splitlines())

    def test_object_diff_add_blob(self):
        f = StringIO()
        store = MemoryObjectStore()
        b2 = Blob.from_string("new\nsame\n")
        store.add_object(b2)
        write_object_diff(f, store, (None, None, None),
                                    ("bar.txt", 0644, b2.id))
        self.assertEqual([
            'diff --git /dev/null b/bar.txt',
             'new mode 644',
             'index 0000000..a116b51 644',
             '--- /dev/null',
             '+++ b/bar.txt',
             '@@ -1,0 +1,2 @@',
             '+new',
             '+same'
            ], f.getvalue().splitlines())

    def test_object_diff_remove_blob(self):
        f = StringIO()
        b1 = Blob.from_string("new\nsame\n")
        store = MemoryObjectStore()
        store.add_object(b1)
        write_object_diff(f, store, ("bar.txt", 0644, b1.id),
                                    (None, None, None))
        self.assertEqual([
            'diff --git a/bar.txt /dev/null',
            'deleted mode 644',
            'index a116b51..0000000',
            '--- a/bar.txt',
            '+++ /dev/null',
            '@@ -1,2 +1,0 @@',
            '-new',
            '-same'
            ], f.getvalue().splitlines())

    def test_object_diff_bin_blob_force(self):
        f = StringIO()
        # Prepare two slightly different PNG headers
        b1 = Blob.from_string(
            "\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52"
            "\x00\x00\x01\xd5\x00\x00\x00\x9f\x08\x04\x00\x00\x00\x05\x04\x8b")
        b2 = Blob.from_string(
            "\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52"
            "\x00\x00\x01\xd5\x00\x00\x00\x9f\x08\x03\x00\x00\x00\x98\xd3\xb3")
        store = MemoryObjectStore()
        store.add_objects([(b1, None), (b2, None)])
        write_object_diff(f, store, ('foo.png', 0644, b1.id),
                                    ('bar.png', 0644, b2.id), diff_binary=True)
        self.assertEqual([
            'diff --git a/foo.png b/bar.png',
            'index f73e47d..06364b7 644',
            '--- a/foo.png',
            '+++ b/bar.png',
            '@@ -1,4 +1,4 @@',
            ' \x89PNG',
            ' \x1a',
            ' \x00\x00\x00',
            '-IHDR\x00\x00\x01\xd5\x00\x00\x00\x9f\x08\x04\x00\x00\x00\x05\x04\x8b',
            '\\ No newline at end of file',
            '+IHDR\x00\x00\x01\xd5\x00\x00\x00\x9f\x08\x03\x00\x00\x00\x98\xd3\xb3',
            '\\ No newline at end of file'
            ], f.getvalue().splitlines())

    def test_object_diff_bin_blob(self):
        f = StringIO()
        # Prepare two slightly different PNG headers
        b1 = Blob.from_string(
            "\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52"
            "\x00\x00\x01\xd5\x00\x00\x00\x9f\x08\x04\x00\x00\x00\x05\x04\x8b")
        b2 = Blob.from_string(
            "\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52"
            "\x00\x00\x01\xd5\x00\x00\x00\x9f\x08\x03\x00\x00\x00\x98\xd3\xb3")
        store = MemoryObjectStore()
        store.add_objects([(b1, None), (b2, None)])
        write_object_diff(f, store, ('foo.png', 0644, b1.id),
                                    ('bar.png', 0644, b2.id))
        self.assertEqual([
            'diff --git a/foo.png b/bar.png',
            'index f73e47d..06364b7 644',
            'Binary files a/foo.png and b/bar.png differ'
            ], f.getvalue().splitlines())

    def test_object_diff_add_bin_blob(self):
        f = StringIO()
        b2 = Blob.from_string(
            '\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52'
            '\x00\x00\x01\xd5\x00\x00\x00\x9f\x08\x03\x00\x00\x00\x98\xd3\xb3')
        store = MemoryObjectStore()
        store.add_object(b2)
        write_object_diff(f, store, (None, None, None),
                                    ('bar.png', 0644, b2.id))
        self.assertEqual([
            'diff --git /dev/null b/bar.png',
            'new mode 644',
            'index 0000000..06364b7 644',
            'Binary files /dev/null and b/bar.png differ'
            ], f.getvalue().splitlines())

    def test_object_diff_remove_bin_blob(self):
        f = StringIO()
        b1 = Blob.from_string(
            '\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52'
            '\x00\x00\x01\xd5\x00\x00\x00\x9f\x08\x04\x00\x00\x00\x05\x04\x8b')
        store = MemoryObjectStore()
        store.add_object(b1)
        write_object_diff(f, store, ('foo.png', 0644, b1.id),
                                    (None, None, None))
        self.assertEqual([
            'diff --git a/foo.png /dev/null',
            'deleted mode 644',
            'index f73e47d..0000000',
            'Binary files a/foo.png and /dev/null differ'
            ], f.getvalue().splitlines())

    def test_object_diff_kind_change(self):
        f = StringIO()
        b1 = Blob.from_string("new\nsame\n")
        store = MemoryObjectStore()
        store.add_object(b1)
        write_object_diff(f, store, ("bar.txt", 0644, b1.id),
            ("bar.txt", 0160000, "06d0bdd9e2e20377b3180e4986b14c8549b393e4"))
        self.assertEqual([
            'diff --git a/bar.txt b/bar.txt',
            'old mode 644',
            'new mode 160000',
            'index a116b51..06d0bdd 160000',
            '--- a/bar.txt',
            '+++ b/bar.txt',
            '@@ -1,2 +1,1 @@',
            '-new',
            '-same',
            '+Submodule commit 06d0bdd9e2e20377b3180e4986b14c8549b393e4',
            ], f.getvalue().splitlines())

########NEW FILE########
__FILENAME__ = test_protocol
# test_protocol.py -- Tests for the git protocol
# Copyright (C) 2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for the smart protocol utility functions."""


from StringIO import StringIO

from dulwich.errors import (
    HangupException,
    )
from dulwich.protocol import (
    PktLineParser,
    Protocol,
    ReceivableProtocol,
    extract_capabilities,
    extract_want_line_capabilities,
    ack_type,
    SINGLE_ACK,
    MULTI_ACK,
    MULTI_ACK_DETAILED,
    BufferedPktLineWriter,
    )
from dulwich.tests import TestCase


class BaseProtocolTests(object):

    def test_write_pkt_line_none(self):
        self.proto.write_pkt_line(None)
        self.assertEqual(self.rout.getvalue(), '0000')

    def test_write_pkt_line(self):
        self.proto.write_pkt_line('bla')
        self.assertEqual(self.rout.getvalue(), '0007bla')

    def test_read_pkt_line(self):
        self.rin.write('0008cmd ')
        self.rin.seek(0)
        self.assertEqual('cmd ', self.proto.read_pkt_line())

    def test_eof(self):
        self.rin.write('0000')
        self.rin.seek(0)
        self.assertFalse(self.proto.eof())
        self.assertEqual(None, self.proto.read_pkt_line())
        self.assertTrue(self.proto.eof())
        self.assertRaises(HangupException, self.proto.read_pkt_line)

    def test_unread_pkt_line(self):
        self.rin.write('0007foo0000')
        self.rin.seek(0)
        self.assertEqual('foo', self.proto.read_pkt_line())
        self.proto.unread_pkt_line('bar')
        self.assertEqual('bar', self.proto.read_pkt_line())
        self.assertEqual(None, self.proto.read_pkt_line())
        self.proto.unread_pkt_line('baz1')
        self.assertRaises(ValueError, self.proto.unread_pkt_line, 'baz2')

    def test_read_pkt_seq(self):
        self.rin.write('0008cmd 0005l0000')
        self.rin.seek(0)
        self.assertEqual(['cmd ', 'l'], list(self.proto.read_pkt_seq()))

    def test_read_pkt_line_none(self):
        self.rin.write('0000')
        self.rin.seek(0)
        self.assertEqual(None, self.proto.read_pkt_line())

    def test_write_sideband(self):
        self.proto.write_sideband(3, 'bloe')
        self.assertEqual(self.rout.getvalue(), '0009\x03bloe')

    def test_send_cmd(self):
        self.proto.send_cmd('fetch', 'a', 'b')
        self.assertEqual(self.rout.getvalue(), '000efetch a\x00b\x00')

    def test_read_cmd(self):
        self.rin.write('0012cmd arg1\x00arg2\x00')
        self.rin.seek(0)
        self.assertEqual(('cmd', ['arg1', 'arg2']), self.proto.read_cmd())

    def test_read_cmd_noend0(self):
        self.rin.write('0011cmd arg1\x00arg2')
        self.rin.seek(0)
        self.assertRaises(AssertionError, self.proto.read_cmd)


class ProtocolTests(BaseProtocolTests, TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.rout = StringIO()
        self.rin = StringIO()
        self.proto = Protocol(self.rin.read, self.rout.write)


class ReceivableStringIO(StringIO):
    """StringIO with socket-like recv semantics for testing."""

    def __init__(self):
        StringIO.__init__(self)
        self.allow_read_past_eof = False

    def recv(self, size):
        # fail fast if no bytes are available; in a real socket, this would
        # block forever
        if self.tell() == len(self.getvalue()) and not self.allow_read_past_eof:
            raise AssertionError('Blocking read past end of socket')
        if size == 1:
            return self.read(1)
        # calls shouldn't return quite as much as asked for
        return self.read(size - 1)


class ReceivableProtocolTests(BaseProtocolTests, TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.rout = StringIO()
        self.rin = ReceivableStringIO()
        self.proto = ReceivableProtocol(self.rin.recv, self.rout.write)
        self.proto._rbufsize = 8

    def test_eof(self):
        # Allow blocking reads past EOF just for this test. The only parts of
        # the protocol that might check for EOF do not depend on the recv()
        # semantics anyway.
        self.rin.allow_read_past_eof = True
        BaseProtocolTests.test_eof(self)

    def test_recv(self):
        all_data = '1234567' * 10  # not a multiple of bufsize
        self.rin.write(all_data)
        self.rin.seek(0)
        data = ''
        # We ask for 8 bytes each time and actually read 7, so it should take
        # exactly 10 iterations.
        for _ in xrange(10):
            data += self.proto.recv(10)
        # any more reads would block
        self.assertRaises(AssertionError, self.proto.recv, 10)
        self.assertEqual(all_data, data)

    def test_recv_read(self):
        all_data = '1234567'  # recv exactly in one call
        self.rin.write(all_data)
        self.rin.seek(0)
        self.assertEqual('1234', self.proto.recv(4))
        self.assertEqual('567', self.proto.read(3))
        self.assertRaises(AssertionError, self.proto.recv, 10)

    def test_read_recv(self):
        all_data = '12345678abcdefg'
        self.rin.write(all_data)
        self.rin.seek(0)
        self.assertEqual('1234', self.proto.read(4))
        self.assertEqual('5678abc', self.proto.recv(8))
        self.assertEqual('defg', self.proto.read(4))
        self.assertRaises(AssertionError, self.proto.recv, 10)

    def test_mixed(self):
        # arbitrary non-repeating string
        all_data = ','.join(str(i) for i in xrange(100))
        self.rin.write(all_data)
        self.rin.seek(0)
        data = ''

        for i in xrange(1, 100):
            data += self.proto.recv(i)
            # if we get to the end, do a non-blocking read instead of blocking
            if len(data) + i > len(all_data):
                data += self.proto.recv(i)
                # ReceivableStringIO leaves off the last byte unless we ask
                # nicely
                data += self.proto.recv(1)
                break
            else:
                data += self.proto.read(i)
        else:
            # didn't break, something must have gone wrong
            self.fail()

        self.assertEqual(all_data, data)


class CapabilitiesTestCase(TestCase):

    def test_plain(self):
        self.assertEqual(('bla', []), extract_capabilities('bla'))

    def test_caps(self):
        self.assertEqual(('bla', ['la']), extract_capabilities('bla\0la'))
        self.assertEqual(('bla', ['la']), extract_capabilities('bla\0la\n'))
        self.assertEqual(('bla', ['la', 'la']), extract_capabilities('bla\0la la'))

    def test_plain_want_line(self):
        self.assertEqual(('want bla', []), extract_want_line_capabilities('want bla'))

    def test_caps_want_line(self):
        self.assertEqual(('want bla', ['la']), extract_want_line_capabilities('want bla la'))
        self.assertEqual(('want bla', ['la']), extract_want_line_capabilities('want bla la\n'))
        self.assertEqual(('want bla', ['la', 'la']), extract_want_line_capabilities('want bla la la'))

    def test_ack_type(self):
        self.assertEqual(SINGLE_ACK, ack_type(['foo', 'bar']))
        self.assertEqual(MULTI_ACK, ack_type(['foo', 'bar', 'multi_ack']))
        self.assertEqual(MULTI_ACK_DETAILED,
                          ack_type(['foo', 'bar', 'multi_ack_detailed']))
        # choose detailed when both present
        self.assertEqual(MULTI_ACK_DETAILED,
                          ack_type(['foo', 'bar', 'multi_ack',
                                    'multi_ack_detailed']))


class BufferedPktLineWriterTests(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self._output = StringIO()
        self._writer = BufferedPktLineWriter(self._output.write, bufsize=16)

    def assertOutputEquals(self, expected):
        self.assertEqual(expected, self._output.getvalue())

    def _truncate(self):
        self._output.seek(0)
        self._output.truncate()

    def test_write(self):
        self._writer.write('foo')
        self.assertOutputEquals('')
        self._writer.flush()
        self.assertOutputEquals('0007foo')

    def test_write_none(self):
        self._writer.write(None)
        self.assertOutputEquals('')
        self._writer.flush()
        self.assertOutputEquals('0000')

    def test_flush_empty(self):
        self._writer.flush()
        self.assertOutputEquals('')

    def test_write_multiple(self):
        self._writer.write('foo')
        self._writer.write('bar')
        self.assertOutputEquals('')
        self._writer.flush()
        self.assertOutputEquals('0007foo0007bar')

    def test_write_across_boundary(self):
        self._writer.write('foo')
        self._writer.write('barbaz')
        self.assertOutputEquals('0007foo000abarba')
        self._truncate()
        self._writer.flush()
        self.assertOutputEquals('z')

    def test_write_to_boundary(self):
        self._writer.write('foo')
        self._writer.write('barba')
        self.assertOutputEquals('0007foo0009barba')
        self._truncate()
        self._writer.write('z')
        self._writer.flush()
        self.assertOutputEquals('0005z')


class PktLineParserTests(TestCase):

    def test_none(self):
        pktlines = []
        parser = PktLineParser(pktlines.append)
        parser.parse("0000")
        self.assertEqual(pktlines, [None])
        self.assertEqual("", parser.get_tail())

    def test_small_fragments(self):
        pktlines = []
        parser = PktLineParser(pktlines.append)
        parser.parse("00")
        parser.parse("05")
        parser.parse("z0000")
        self.assertEqual(pktlines, ["z", None])
        self.assertEqual("", parser.get_tail())

    def test_multiple_packets(self):
        pktlines = []
        parser = PktLineParser(pktlines.append)
        parser.parse("0005z0006aba")
        self.assertEqual(pktlines, ["z", "ab"])
        self.assertEqual("a", parser.get_tail())

########NEW FILE########
__FILENAME__ = test_repository
# test_repository.py -- tests for repository.py
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for the repository."""

from cStringIO import StringIO
import os
import stat
import shutil
import tempfile
import warnings

from dulwich import errors
from dulwich.file import (
    GitFile,
    )
from dulwich.object_store import (
    tree_lookup_path,
    )
from dulwich import objects
from dulwich.config import Config
from dulwich.repo import (
    check_ref_format,
    DictRefsContainer,
    InfoRefsContainer,
    Repo,
    MemoryRepo,
    read_packed_refs,
    read_packed_refs_with_peeled,
    write_packed_refs,
    _split_ref_line,
    )
from dulwich.tests import (
    TestCase,
    )
from dulwich.tests.utils import (
    open_repo,
    tear_down_repo,
    setup_warning_catcher,
    )

missing_sha = 'b91fa4d900e17e99b433218e988c4eb4a3e9a097'


class CreateRepositoryTests(TestCase):

    def assertFileContentsEqual(self, expected, repo, path):
        f = repo.get_named_file(path)
        if not f:
            self.assertEqual(expected, None)
        else:
            try:
                self.assertEqual(expected, f.read())
            finally:
                f.close()

    def _check_repo_contents(self, repo, expect_bare):
        self.assertEqual(expect_bare, repo.bare)
        self.assertFileContentsEqual('Unnamed repository', repo, 'description')
        self.assertFileContentsEqual('', repo, os.path.join('info', 'exclude'))
        self.assertFileContentsEqual(None, repo, 'nonexistent file')
        barestr = 'bare = %s' % str(expect_bare).lower()
        config_text = repo.get_named_file('config').read()
        self.assertTrue(barestr in config_text, "%r" % config_text)

    def test_create_disk_bare(self):
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        repo = Repo.init_bare(tmp_dir)
        self.assertEqual(tmp_dir, repo._controldir)
        self._check_repo_contents(repo, True)

    def test_create_disk_non_bare(self):
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        repo = Repo.init(tmp_dir)
        self.assertEqual(os.path.join(tmp_dir, '.git'), repo._controldir)
        self._check_repo_contents(repo, False)

    def test_create_memory(self):
        repo = MemoryRepo.init_bare([], {})
        self._check_repo_contents(repo, True)


class RepositoryTests(TestCase):

    def setUp(self):
        super(RepositoryTests, self).setUp()
        self._repo = None

    def tearDown(self):
        if self._repo is not None:
            tear_down_repo(self._repo)
        super(RepositoryTests, self).tearDown()

    def test_simple_props(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual(r.controldir(), r.path)

    def test_ref(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual(r.ref('refs/heads/master'),
                         'a90fa2d900a17e99b433217e988c4eb4a2e9a097')

    def test_setitem(self):
        r = self._repo = open_repo('a.git')
        r["refs/tags/foo"] = 'a90fa2d900a17e99b433217e988c4eb4a2e9a097'
        self.assertEqual('a90fa2d900a17e99b433217e988c4eb4a2e9a097',
                          r["refs/tags/foo"].id)

    def test_delitem(self):
        r = self._repo = open_repo('a.git')

        del r['refs/heads/master']
        self.assertRaises(KeyError, lambda: r['refs/heads/master'])

        del r['HEAD']
        self.assertRaises(KeyError, lambda: r['HEAD'])

        self.assertRaises(ValueError, r.__delitem__, 'notrefs/foo')

    def test_get_refs(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual({
            'HEAD': 'a90fa2d900a17e99b433217e988c4eb4a2e9a097',
            'refs/heads/master': 'a90fa2d900a17e99b433217e988c4eb4a2e9a097',
            'refs/tags/mytag': '28237f4dc30d0d462658d6b937b08a0f0b6ef55a',
            'refs/tags/mytag-packed': 'b0931cadc54336e78a1d980420e3268903b57a50',
            }, r.get_refs())

    def test_head(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual(r.head(), 'a90fa2d900a17e99b433217e988c4eb4a2e9a097')

    def test_get_object(self):
        r = self._repo = open_repo('a.git')
        obj = r.get_object(r.head())
        self.assertEqual(obj.type_name, 'commit')

    def test_get_object_non_existant(self):
        r = self._repo = open_repo('a.git')
        self.assertRaises(KeyError, r.get_object, missing_sha)

    def test_contains_object(self):
        r = self._repo = open_repo('a.git')
        self.assertTrue(r.head() in r)

    def test_contains_ref(self):
        r = self._repo = open_repo('a.git')
        self.assertTrue("HEAD" in r)

    def test_get_no_description(self):
        r = self._repo = open_repo('a.git')
        self.assertIs(None, r.get_description())

    def test_get_description(self):
        r = self._repo = open_repo('a.git')
        f = open(os.path.join(r.path, 'description'), 'w')
        try:
            f.write("Some description")
        finally:
            f.close()
        self.assertEquals("Some description", r.get_description())

    def test_contains_missing(self):
        r = self._repo = open_repo('a.git')
        self.assertFalse("bar" in r)

    def test_commit(self):
        r = self._repo = open_repo('a.git')
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        obj = r.commit(r.head())
        self.assertEqual(obj.type_name, 'commit')

    def test_commit_not_commit(self):
        r = self._repo = open_repo('a.git')
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        self.assertRaises(errors.NotCommitError,
            r.commit, '4f2e6529203aa6d44b5af6e3292c837ceda003f9')

    def test_tree(self):
        r = self._repo = open_repo('a.git')
        commit = r[r.head()]
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        tree = r.tree(commit.tree)
        self.assertEqual(tree.type_name, 'tree')
        self.assertEqual(tree.sha().hexdigest(), commit.tree)

    def test_tree_not_tree(self):
        r = self._repo = open_repo('a.git')
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        self.assertRaises(errors.NotTreeError, r.tree, r.head())

    def test_tag(self):
        r = self._repo = open_repo('a.git')
        tag_sha = '28237f4dc30d0d462658d6b937b08a0f0b6ef55a'
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        tag = r.tag(tag_sha)
        self.assertEqual(tag.type_name, 'tag')
        self.assertEqual(tag.sha().hexdigest(), tag_sha)
        obj_class, obj_sha = tag.object
        self.assertEqual(obj_class, objects.Commit)
        self.assertEqual(obj_sha, r.head())

    def test_tag_not_tag(self):
        r = self._repo = open_repo('a.git')
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        self.assertRaises(errors.NotTagError, r.tag, r.head())

    def test_get_peeled(self):
        # unpacked ref
        r = self._repo = open_repo('a.git')
        tag_sha = '28237f4dc30d0d462658d6b937b08a0f0b6ef55a'
        self.assertNotEqual(r[tag_sha].sha().hexdigest(), r.head())
        self.assertEqual(r.get_peeled('refs/tags/mytag'), r.head())

        # packed ref with cached peeled value
        packed_tag_sha = 'b0931cadc54336e78a1d980420e3268903b57a50'
        parent_sha = r[r.head()].parents[0]
        self.assertNotEqual(r[packed_tag_sha].sha().hexdigest(), parent_sha)
        self.assertEqual(r.get_peeled('refs/tags/mytag-packed'), parent_sha)

        # TODO: add more corner cases to test repo

    def test_get_peeled_not_tag(self):
        r = self._repo = open_repo('a.git')
        self.assertEqual(r.get_peeled('HEAD'), r.head())

    def test_get_blob(self):
        r = self._repo = open_repo('a.git')
        commit = r[r.head()]
        tree = r[commit.tree]
        blob_sha = tree.items()[0][2]
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        blob = r.get_blob(blob_sha)
        self.assertEqual(blob.type_name, 'blob')
        self.assertEqual(blob.sha().hexdigest(), blob_sha)

    def test_get_blob_notblob(self):
        r = self._repo = open_repo('a.git')
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        self.assertRaises(errors.NotBlobError, r.get_blob, r.head())

    def test_get_walker(self):
        r = self._repo = open_repo('a.git')
        # include defaults to [r.head()]
        self.assertEqual([e.commit.id for e in r.get_walker()],
                         [r.head(), '2a72d929692c41d8554c07f6301757ba18a65d91'])
        self.assertEqual(
            [e.commit.id for e in r.get_walker(['2a72d929692c41d8554c07f6301757ba18a65d91'])],
            ['2a72d929692c41d8554c07f6301757ba18a65d91'])
        self.assertEqual(
            [e.commit.id for e in r.get_walker('2a72d929692c41d8554c07f6301757ba18a65d91')],
            ['2a72d929692c41d8554c07f6301757ba18a65d91'])

    def test_linear_history(self):
        r = self._repo = open_repo('a.git')
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        history = r.revision_history(r.head())
        shas = [c.sha().hexdigest() for c in history]
        self.assertEqual(shas, [r.head(),
                                '2a72d929692c41d8554c07f6301757ba18a65d91'])

    def test_clone(self):
        r = self._repo = open_repo('a.git')
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        t = r.clone(tmp_dir, mkdir=False)
        self.assertEqual({
            'HEAD': 'a90fa2d900a17e99b433217e988c4eb4a2e9a097',
            'refs/remotes/origin/master':
                'a90fa2d900a17e99b433217e988c4eb4a2e9a097',
            'refs/heads/master': 'a90fa2d900a17e99b433217e988c4eb4a2e9a097',
            'refs/tags/mytag': '28237f4dc30d0d462658d6b937b08a0f0b6ef55a',
            'refs/tags/mytag-packed':
                'b0931cadc54336e78a1d980420e3268903b57a50',
            }, t.refs.as_dict())
        shas = [e.commit.id for e in r.get_walker()]
        self.assertEqual(shas, [t.head(),
                         '2a72d929692c41d8554c07f6301757ba18a65d91'])

    def test_clone_no_head(self):
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        repo_dir = os.path.join(os.path.dirname(__file__), 'data', 'repos')
        dest_dir = os.path.join(temp_dir, 'a.git')
        shutil.copytree(os.path.join(repo_dir, 'a.git'),
                        dest_dir, symlinks=True)
        r = Repo(dest_dir)
        del r.refs["refs/heads/master"]
        del r.refs["HEAD"]
        t = r.clone(os.path.join(temp_dir, 'b.git'), mkdir=True)
        self.assertEqual({
            'refs/tags/mytag': '28237f4dc30d0d462658d6b937b08a0f0b6ef55a',
            'refs/tags/mytag-packed':
                'b0931cadc54336e78a1d980420e3268903b57a50',
            }, t.refs.as_dict())

    def test_clone_empty(self):
        """Test clone() doesn't crash if HEAD points to a non-existing ref.

        This simulates cloning server-side bare repository either when it is
        still empty or if user renames master branch and pushes private repo
        to the server.
        Non-bare repo HEAD always points to an existing ref.
        """
        r = self._repo = open_repo('empty.git')
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)
        r.clone(tmp_dir, mkdir=False, bare=True)

    def test_merge_history(self):
        r = self._repo = open_repo('simple_merge.git')
        shas = [e.commit.id for e in r.get_walker()]
        self.assertEqual(shas, ['5dac377bdded4c9aeb8dff595f0faeebcc8498cc',
                                'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                                '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6',
                                '60dacdc733de308bb77bb76ce0fb0f9b44c9769e',
                                '0d89f20333fbb1d2f3a94da77f4981373d8f4310'])

    def test_revision_history_missing_commit(self):
        r = self._repo = open_repo('simple_merge.git')
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)
        self.assertRaises(errors.MissingCommitError, r.revision_history,
                          missing_sha)

    def test_out_of_order_merge(self):
        """Test that revision history is ordered by date, not parent order."""
        r = self._repo = open_repo('ooo_merge.git')
        shas = [e.commit.id for e in r.get_walker()]
        self.assertEqual(shas, ['7601d7f6231db6a57f7bbb79ee52e4d462fd44d1',
                                'f507291b64138b875c28e03469025b1ea20bc614',
                                'fb5b0425c7ce46959bec94d54b9a157645e114f5',
                                'f9e39b120c68182a4ba35349f832d0e4e61f485c'])

    def test_get_tags_empty(self):
        r = self._repo = open_repo('ooo_merge.git')
        self.assertEqual({}, r.refs.as_dict('refs/tags'))

    def test_get_config(self):
        r = self._repo = open_repo('ooo_merge.git')
        self.assertIsInstance(r.get_config(), Config)

    def test_get_config_stack(self):
        r = self._repo = open_repo('ooo_merge.git')
        self.assertIsInstance(r.get_config_stack(), Config)

    def test_submodule(self):
        temp_dir = tempfile.mkdtemp()
        repo_dir = os.path.join(os.path.dirname(__file__), 'data', 'repos')
        shutil.copytree(os.path.join(repo_dir, 'a.git'),
                        os.path.join(temp_dir, 'a.git'), symlinks=True)
        rel = os.path.relpath(os.path.join(repo_dir, 'submodule'), temp_dir)
        os.symlink(os.path.join(rel, 'dotgit'), os.path.join(temp_dir, '.git'))
        r = Repo(temp_dir)
        self.assertEqual(r.head(), 'a90fa2d900a17e99b433217e988c4eb4a2e9a097')

    def test_common_revisions(self):
        """
        This test demonstrates that ``find_common_revisions()`` actually returns
        common heads, not revisions; dulwich already uses
        ``find_common_revisions()`` in such a manner (see
        ``Repo.fetch_objects()``).
        """

        expected_shas = set(['60dacdc733de308bb77bb76ce0fb0f9b44c9769e'])

        # Source for objects.
        r_base = open_repo('simple_merge.git')

        # Re-create each-side of the merge in simple_merge.git.
        #
        # Since the trees and blobs are missing, the repository created is
        # corrupted, but we're only checking for commits for the purpose of this
        # test, so it's immaterial.
        r1_dir = tempfile.mkdtemp()
        r1_commits = ['ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd', # HEAD
                      '60dacdc733de308bb77bb76ce0fb0f9b44c9769e',
                      '0d89f20333fbb1d2f3a94da77f4981373d8f4310']

        r2_dir = tempfile.mkdtemp()
        r2_commits = ['4cffe90e0a41ad3f5190079d7c8f036bde29cbe6', # HEAD
                      '60dacdc733de308bb77bb76ce0fb0f9b44c9769e',
                      '0d89f20333fbb1d2f3a94da77f4981373d8f4310']

        try:
            r1 = Repo.init_bare(r1_dir)
            map(lambda c: r1.object_store.add_object(r_base.get_object(c)), \
                r1_commits)
            r1.refs['HEAD'] = r1_commits[0]

            r2 = Repo.init_bare(r2_dir)
            map(lambda c: r2.object_store.add_object(r_base.get_object(c)), \
                r2_commits)
            r2.refs['HEAD'] = r2_commits[0]

            # Finally, the 'real' testing!
            shas = r2.object_store.find_common_revisions(r1.get_graph_walker())
            self.assertEqual(set(shas), expected_shas)

            shas = r1.object_store.find_common_revisions(r2.get_graph_walker())
            self.assertEqual(set(shas), expected_shas)
        finally:
            shutil.rmtree(r1_dir)
            shutil.rmtree(r2_dir)

    def test_shell_hook_pre_commit(self):
        if os.name != 'posix':
            self.skipTest('shell hook tests requires POSIX shell')

        pre_commit_fail = """#!/bin/sh
exit 1
"""

        pre_commit_success = """#!/bin/sh
exit 0
"""

        repo_dir = os.path.join(tempfile.mkdtemp())
        r = Repo.init(repo_dir)
        self.addCleanup(shutil.rmtree, repo_dir)

        pre_commit = os.path.join(r.controldir(), 'hooks', 'pre-commit')

        f = open(pre_commit, 'wb')
        try:
            f.write(pre_commit_fail)
        finally:
            f.close()
        os.chmod(pre_commit, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        self.assertRaises(errors.CommitError, r.do_commit, 'failed commit',
                          committer='Test Committer <test@nodomain.com>',
                          author='Test Author <test@nodomain.com>',
                          commit_timestamp=12345, commit_timezone=0,
                          author_timestamp=12345, author_timezone=0)

        f = open(pre_commit, 'wb')
        try:
            f.write(pre_commit_success)
        finally:
            f.close()
        os.chmod(pre_commit, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        commit_sha = r.do_commit(
            'empty commit',
            committer='Test Committer <test@nodomain.com>',
            author='Test Author <test@nodomain.com>',
            commit_timestamp=12395, commit_timezone=0,
            author_timestamp=12395, author_timezone=0)
        self.assertEqual([], r[commit_sha].parents)

    def test_shell_hook_commit_msg(self):
        if os.name != 'posix':
            self.skipTest('shell hook tests requires POSIX shell')

        commit_msg_fail = """#!/bin/sh
exit 1
"""

        commit_msg_success = """#!/bin/sh
exit 0
"""

        repo_dir = os.path.join(tempfile.mkdtemp())
        r = Repo.init(repo_dir)
        self.addCleanup(shutil.rmtree, repo_dir)

        commit_msg = os.path.join(r.controldir(), 'hooks', 'commit-msg')

        f = open(commit_msg, 'wb')
        try:
            f.write(commit_msg_fail)
        finally:
            f.close()
        os.chmod(commit_msg, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        self.assertRaises(errors.CommitError, r.do_commit, 'failed commit',
                          committer='Test Committer <test@nodomain.com>',
                          author='Test Author <test@nodomain.com>',
                          commit_timestamp=12345, commit_timezone=0,
                          author_timestamp=12345, author_timezone=0)

        f = open(commit_msg, 'wb')
        try:
            f.write(commit_msg_success)
        finally:
            f.close()
        os.chmod(commit_msg, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        commit_sha = r.do_commit(
            'empty commit',
            committer='Test Committer <test@nodomain.com>',
            author='Test Author <test@nodomain.com>',
            commit_timestamp=12395, commit_timezone=0,
            author_timestamp=12395, author_timezone=0)
        self.assertEqual([], r[commit_sha].parents)

    def test_shell_hook_post_commit(self):
        if os.name != 'posix':
            self.skipTest('shell hook tests requires POSIX shell')

        repo_dir = os.path.join(tempfile.mkdtemp())
        r = Repo.init(repo_dir)
        self.addCleanup(shutil.rmtree, repo_dir)

        (fd, path) = tempfile.mkstemp(dir=repo_dir)
        post_commit_msg = """#!/bin/sh
unlink %(file)s
""" % {'file': path}

        root_sha = r.do_commit(
            'empty commit',
            committer='Test Committer <test@nodomain.com>',
            author='Test Author <test@nodomain.com>',
            commit_timestamp=12345, commit_timezone=0,
            author_timestamp=12345, author_timezone=0)
        self.assertEqual([], r[root_sha].parents)

        post_commit = os.path.join(r.controldir(), 'hooks', 'post-commit')

        f = open(post_commit, 'wb')
        try:
            f.write(post_commit_msg)
        finally:
            f.close()
        os.chmod(post_commit, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        commit_sha = r.do_commit(
            'empty commit',
            committer='Test Committer <test@nodomain.com>',
            author='Test Author <test@nodomain.com>',
            commit_timestamp=12345, commit_timezone=0,
            author_timestamp=12345, author_timezone=0)
        self.assertEqual([root_sha], r[commit_sha].parents)

        self.assertFalse(os.path.exists(path))

        post_commit_msg_fail = """#!/bin/sh
exit 1
"""
        f = open(post_commit, 'wb')
        try:
            f.write(post_commit_msg_fail)
        finally:
            f.close()
        os.chmod(post_commit, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

        warnings.simplefilter("always", UserWarning)
        self.addCleanup(warnings.resetwarnings)
        warnings_list = setup_warning_catcher()

        commit_sha2 = r.do_commit(
            'empty commit',
            committer='Test Committer <test@nodomain.com>',
            author='Test Author <test@nodomain.com>',
            commit_timestamp=12345, commit_timezone=0,
            author_timestamp=12345, author_timezone=0)
        self.assertEqual(len(warnings_list), 1)
        self.assertIsInstance(warnings_list[-1], UserWarning)
        self.assertTrue("post-commit hook failed: " in str(warnings_list[-1]))
        self.assertEqual([commit_sha], r[commit_sha2].parents)


class BuildRepoTests(TestCase):
    """Tests that build on-disk repos from scratch.

    Repos live in a temp dir and are torn down after each test. They start with
    a single commit in master having single file named 'a'.
    """

    def setUp(self):
        super(BuildRepoTests, self).setUp()
        repo_dir = os.path.join(tempfile.mkdtemp(), 'test')
        os.makedirs(repo_dir)
        r = self._repo = Repo.init(repo_dir)
        self.assertFalse(r.bare)
        self.assertEqual('ref: refs/heads/master', r.refs.read_ref('HEAD'))
        self.assertRaises(KeyError, lambda: r.refs['refs/heads/master'])

        f = open(os.path.join(r.path, 'a'), 'wb')
        try:
            f.write('file contents')
        finally:
            f.close()
        r.stage(['a'])
        commit_sha = r.do_commit('msg',
                                 committer='Test Committer <test@nodomain.com>',
                                 author='Test Author <test@nodomain.com>',
                                 commit_timestamp=12345, commit_timezone=0,
                                 author_timestamp=12345, author_timezone=0)
        self.assertEqual([], r[commit_sha].parents)
        self._root_commit = commit_sha

    def tearDown(self):
        tear_down_repo(self._repo)
        super(BuildRepoTests, self).tearDown()

    def test_build_repo(self):
        r = self._repo
        self.assertEqual('ref: refs/heads/master', r.refs.read_ref('HEAD'))
        self.assertEqual(self._root_commit, r.refs['refs/heads/master'])
        expected_blob = objects.Blob.from_string('file contents')
        self.assertEqual(expected_blob.data, r[expected_blob.id].data)
        actual_commit = r[self._root_commit]
        self.assertEqual('msg', actual_commit.message)

    def test_commit_modified(self):
        r = self._repo
        f = open(os.path.join(r.path, 'a'), 'wb')
        try:
            f.write('new contents')
        finally:
            f.close()
        r.stage(['a'])
        commit_sha = r.do_commit('modified a',
                                 committer='Test Committer <test@nodomain.com>',
                                 author='Test Author <test@nodomain.com>',
                                 commit_timestamp=12395, commit_timezone=0,
                                 author_timestamp=12395, author_timezone=0)
        self.assertEqual([self._root_commit], r[commit_sha].parents)
        _, blob_id = tree_lookup_path(r.get_object, r[commit_sha].tree, 'a')
        self.assertEqual('new contents', r[blob_id].data)

    def test_commit_deleted(self):
        r = self._repo
        os.remove(os.path.join(r.path, 'a'))
        r.stage(['a'])
        commit_sha = r.do_commit('deleted a',
                                 committer='Test Committer <test@nodomain.com>',
                                 author='Test Author <test@nodomain.com>',
                                 commit_timestamp=12395, commit_timezone=0,
                                 author_timestamp=12395, author_timezone=0)
        self.assertEqual([self._root_commit], r[commit_sha].parents)
        self.assertEqual([], list(r.open_index()))
        tree = r[r[commit_sha].tree]
        self.assertEqual([], list(tree.iteritems()))

    def test_commit_encoding(self):
        r = self._repo
        commit_sha = r.do_commit('commit with strange character \xee',
             committer='Test Committer <test@nodomain.com>',
             author='Test Author <test@nodomain.com>',
             commit_timestamp=12395, commit_timezone=0,
             author_timestamp=12395, author_timezone=0,
             encoding="iso8859-1")
        self.assertEqual("iso8859-1", r[commit_sha].encoding)

    def test_commit_config_identity(self):
        # commit falls back to the users' identity if it wasn't specified
        r = self._repo
        c = r.get_config()
        c.set(("user", ), "name", "Jelmer")
        c.set(("user", ), "email", "jelmer@apache.org")
        c.write_to_path()
        commit_sha = r.do_commit('message')
        self.assertEqual(
            "Jelmer <jelmer@apache.org>",
            r[commit_sha].author)
        self.assertEqual(
            "Jelmer <jelmer@apache.org>",
            r[commit_sha].committer)

    def test_commit_fail_ref(self):
        r = self._repo

        def set_if_equals(name, old_ref, new_ref):
            return False
        r.refs.set_if_equals = set_if_equals

        def add_if_new(name, new_ref):
            self.fail('Unexpected call to add_if_new')
        r.refs.add_if_new = add_if_new

        old_shas = set(r.object_store)
        self.assertRaises(errors.CommitError, r.do_commit, 'failed commit',
                          committer='Test Committer <test@nodomain.com>',
                          author='Test Author <test@nodomain.com>',
                          commit_timestamp=12345, commit_timezone=0,
                          author_timestamp=12345, author_timezone=0)
        new_shas = set(r.object_store) - old_shas
        self.assertEqual(1, len(new_shas))
        # Check that the new commit (now garbage) was added.
        new_commit = r[new_shas.pop()]
        self.assertEqual(r[self._root_commit].tree, new_commit.tree)
        self.assertEqual('failed commit', new_commit.message)

    def test_commit_branch(self):
        r = self._repo

        commit_sha = r.do_commit('commit to branch',
             committer='Test Committer <test@nodomain.com>',
             author='Test Author <test@nodomain.com>',
             commit_timestamp=12395, commit_timezone=0,
             author_timestamp=12395, author_timezone=0,
             ref="refs/heads/new_branch")
        self.assertEqual(self._root_commit, r["HEAD"].id)
        self.assertEqual(commit_sha, r["refs/heads/new_branch"].id)
        self.assertEqual([], r[commit_sha].parents)
        self.assertTrue("refs/heads/new_branch" in r)

        new_branch_head = commit_sha

        commit_sha = r.do_commit('commit to branch 2',
             committer='Test Committer <test@nodomain.com>',
             author='Test Author <test@nodomain.com>',
             commit_timestamp=12395, commit_timezone=0,
             author_timestamp=12395, author_timezone=0,
             ref="refs/heads/new_branch")
        self.assertEqual(self._root_commit, r["HEAD"].id)
        self.assertEqual(commit_sha, r["refs/heads/new_branch"].id)
        self.assertEqual([new_branch_head], r[commit_sha].parents)

    def test_commit_merge_heads(self):
        r = self._repo
        merge_1 = r.do_commit('commit to branch 2',
             committer='Test Committer <test@nodomain.com>',
             author='Test Author <test@nodomain.com>',
             commit_timestamp=12395, commit_timezone=0,
             author_timestamp=12395, author_timezone=0,
             ref="refs/heads/new_branch")
        commit_sha = r.do_commit('commit with merge',
             committer='Test Committer <test@nodomain.com>',
             author='Test Author <test@nodomain.com>',
             commit_timestamp=12395, commit_timezone=0,
             author_timestamp=12395, author_timezone=0,
             merge_heads=[merge_1])
        self.assertEqual(
            [self._root_commit, merge_1],
            r[commit_sha].parents)

    def test_stage_deleted(self):
        r = self._repo
        os.remove(os.path.join(r.path, 'a'))
        r.stage(['a'])
        r.stage(['a'])  # double-stage a deleted path


class CheckRefFormatTests(TestCase):
    """Tests for the check_ref_format function.

    These are the same tests as in the git test suite.
    """

    def test_valid(self):
        self.assertTrue(check_ref_format('heads/foo'))
        self.assertTrue(check_ref_format('foo/bar/baz'))
        self.assertTrue(check_ref_format('refs///heads/foo'))
        self.assertTrue(check_ref_format('foo./bar'))
        self.assertTrue(check_ref_format('heads/foo@bar'))
        self.assertTrue(check_ref_format('heads/fix.lock.error'))

    def test_invalid(self):
        self.assertFalse(check_ref_format('foo'))
        self.assertFalse(check_ref_format('heads/foo/'))
        self.assertFalse(check_ref_format('./foo'))
        self.assertFalse(check_ref_format('.refs/foo'))
        self.assertFalse(check_ref_format('heads/foo..bar'))
        self.assertFalse(check_ref_format('heads/foo?bar'))
        self.assertFalse(check_ref_format('heads/foo.lock'))
        self.assertFalse(check_ref_format('heads/v@{ation'))
        self.assertFalse(check_ref_format('heads/foo\bar'))


ONES = "1" * 40
TWOS = "2" * 40
THREES = "3" * 40
FOURS = "4" * 40

class PackedRefsFileTests(TestCase):

    def test_split_ref_line_errors(self):
        self.assertRaises(errors.PackedRefsException, _split_ref_line,
                          'singlefield')
        self.assertRaises(errors.PackedRefsException, _split_ref_line,
                          'badsha name')
        self.assertRaises(errors.PackedRefsException, _split_ref_line,
                          '%s bad/../refname' % ONES)

    def test_read_without_peeled(self):
        f = StringIO('# comment\n%s ref/1\n%s ref/2' % (ONES, TWOS))
        self.assertEqual([(ONES, 'ref/1'), (TWOS, 'ref/2')],
                         list(read_packed_refs(f)))

    def test_read_without_peeled_errors(self):
        f = StringIO('%s ref/1\n^%s' % (ONES, TWOS))
        self.assertRaises(errors.PackedRefsException, list, read_packed_refs(f))

    def test_read_with_peeled(self):
        f = StringIO('%s ref/1\n%s ref/2\n^%s\n%s ref/4' % (
          ONES, TWOS, THREES, FOURS))
        self.assertEqual([
          (ONES, 'ref/1', None),
          (TWOS, 'ref/2', THREES),
          (FOURS, 'ref/4', None),
          ], list(read_packed_refs_with_peeled(f)))

    def test_read_with_peeled_errors(self):
        f = StringIO('^%s\n%s ref/1' % (TWOS, ONES))
        self.assertRaises(errors.PackedRefsException, list, read_packed_refs(f))

        f = StringIO('%s ref/1\n^%s\n^%s' % (ONES, TWOS, THREES))
        self.assertRaises(errors.PackedRefsException, list, read_packed_refs(f))

    def test_write_with_peeled(self):
        f = StringIO()
        write_packed_refs(f, {'ref/1': ONES, 'ref/2': TWOS},
                          {'ref/1': THREES})
        self.assertEqual(
          "# pack-refs with: peeled\n%s ref/1\n^%s\n%s ref/2\n" % (
          ONES, THREES, TWOS), f.getvalue())

    def test_write_without_peeled(self):
        f = StringIO()
        write_packed_refs(f, {'ref/1': ONES, 'ref/2': TWOS})
        self.assertEqual("%s ref/1\n%s ref/2\n" % (ONES, TWOS), f.getvalue())


# Dict of refs that we expect all RefsContainerTests subclasses to define.
_TEST_REFS = {
  'HEAD': '42d06bd4b77fed026b154d16493e5deab78f02ec',
  'refs/heads/40-char-ref-aaaaaaaaaaaaaaaaaa': '42d06bd4b77fed026b154d16493e5deab78f02ec',
  'refs/heads/master': '42d06bd4b77fed026b154d16493e5deab78f02ec',
  'refs/heads/packed': '42d06bd4b77fed026b154d16493e5deab78f02ec',
  'refs/tags/refs-0.1': 'df6800012397fb85c56e7418dd4eb9405dee075c',
  'refs/tags/refs-0.2': '3ec9c43c84ff242e3ef4a9fc5bc111fd780a76a8',
  }


class RefsContainerTests(object):

    def test_keys(self):
        actual_keys = set(self._refs.keys())
        self.assertEqual(set(self._refs.allkeys()), actual_keys)
        # ignore the symref loop if it exists
        actual_keys.discard('refs/heads/loop')
        self.assertEqual(set(_TEST_REFS.iterkeys()), actual_keys)

        actual_keys = self._refs.keys('refs/heads')
        actual_keys.discard('loop')
        self.assertEqual(
            ['40-char-ref-aaaaaaaaaaaaaaaaaa', 'master', 'packed'],
            sorted(actual_keys))
        self.assertEqual(['refs-0.1', 'refs-0.2'],
                         sorted(self._refs.keys('refs/tags')))

    def test_as_dict(self):
        # refs/heads/loop does not show up even if it exists
        self.assertEqual(_TEST_REFS, self._refs.as_dict())

    def test_setitem(self):
        self._refs['refs/some/ref'] = '42d06bd4b77fed026b154d16493e5deab78f02ec'
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['refs/some/ref'])
        self.assertRaises(errors.RefFormatError, self._refs.__setitem__,
                          'notrefs/foo', '42d06bd4b77fed026b154d16493e5deab78f02ec')

    def test_set_if_equals(self):
        nines = '9' * 40
        self.assertFalse(self._refs.set_if_equals('HEAD', 'c0ffee', nines))
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['HEAD'])

        self.assertTrue(self._refs.set_if_equals(
          'HEAD', '42d06bd4b77fed026b154d16493e5deab78f02ec', nines))
        self.assertEqual(nines, self._refs['HEAD'])

        self.assertTrue(self._refs.set_if_equals('refs/heads/master', None,
                                                 nines))
        self.assertEqual(nines, self._refs['refs/heads/master'])

    def test_add_if_new(self):
        nines = '9' * 40
        self.assertFalse(self._refs.add_if_new('refs/heads/master', nines))
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['refs/heads/master'])

        self.assertTrue(self._refs.add_if_new('refs/some/ref', nines))
        self.assertEqual(nines, self._refs['refs/some/ref'])

    def test_set_symbolic_ref(self):
        self._refs.set_symbolic_ref('refs/heads/symbolic', 'refs/heads/master')
        self.assertEqual('ref: refs/heads/master',
                         self._refs.read_loose_ref('refs/heads/symbolic'))
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['refs/heads/symbolic'])

    def test_set_symbolic_ref_overwrite(self):
        nines = '9' * 40
        self.assertFalse('refs/heads/symbolic' in self._refs)
        self._refs['refs/heads/symbolic'] = nines
        self.assertEqual(nines, self._refs.read_loose_ref('refs/heads/symbolic'))
        self._refs.set_symbolic_ref('refs/heads/symbolic', 'refs/heads/master')
        self.assertEqual('ref: refs/heads/master',
                         self._refs.read_loose_ref('refs/heads/symbolic'))
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['refs/heads/symbolic'])

    def test_check_refname(self):
        self._refs._check_refname('HEAD')
        self._refs._check_refname('refs/stash')
        self._refs._check_refname('refs/heads/foo')

        self.assertRaises(errors.RefFormatError, self._refs._check_refname,
                          'refs')
        self.assertRaises(errors.RefFormatError, self._refs._check_refname,
                          'notrefs/foo')

    def test_contains(self):
        self.assertTrue('refs/heads/master' in self._refs)
        self.assertFalse('refs/heads/bar' in self._refs)

    def test_delitem(self):
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                          self._refs['refs/heads/master'])
        del self._refs['refs/heads/master']
        self.assertRaises(KeyError, lambda: self._refs['refs/heads/master'])

    def test_remove_if_equals(self):
        self.assertFalse(self._refs.remove_if_equals('HEAD', 'c0ffee'))
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['HEAD'])
        self.assertTrue(self._refs.remove_if_equals(
          'refs/tags/refs-0.2', '3ec9c43c84ff242e3ef4a9fc5bc111fd780a76a8'))
        self.assertFalse('refs/tags/refs-0.2' in self._refs)


class DictRefsContainerTests(RefsContainerTests, TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self._refs = DictRefsContainer(dict(_TEST_REFS))

    def test_invalid_refname(self):
        # FIXME: Move this test into RefsContainerTests, but requires
        # some way of injecting invalid refs.
        self._refs._refs["refs/stash"] = "00" * 20
        expected_refs = dict(_TEST_REFS)
        expected_refs["refs/stash"] = "00" * 20
        self.assertEqual(expected_refs, self._refs.as_dict())


class DiskRefsContainerTests(RefsContainerTests, TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self._repo = open_repo('refs.git')
        self._refs = self._repo.refs

    def tearDown(self):
        tear_down_repo(self._repo)
        TestCase.tearDown(self)

    def test_get_packed_refs(self):
        self.assertEqual({
          'refs/heads/packed': '42d06bd4b77fed026b154d16493e5deab78f02ec',
          'refs/tags/refs-0.1': 'df6800012397fb85c56e7418dd4eb9405dee075c',
          }, self._refs.get_packed_refs())

    def test_get_peeled_not_packed(self):
        # not packed
        self.assertEqual(None, self._refs.get_peeled('refs/tags/refs-0.2'))
        self.assertEqual('3ec9c43c84ff242e3ef4a9fc5bc111fd780a76a8',
                         self._refs['refs/tags/refs-0.2'])

        # packed, known not peelable
        self.assertEqual(self._refs['refs/heads/packed'],
                         self._refs.get_peeled('refs/heads/packed'))

        # packed, peeled
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs.get_peeled('refs/tags/refs-0.1'))

    def test_setitem(self):
        RefsContainerTests.test_setitem(self)
        f = open(os.path.join(self._refs.path, 'refs', 'some', 'ref'), 'rb')
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                          f.read()[:40])
        f.close()

    def test_setitem_symbolic(self):
        ones = '1' * 40
        self._refs['HEAD'] = ones
        self.assertEqual(ones, self._refs['HEAD'])

        # ensure HEAD was not modified
        f = open(os.path.join(self._refs.path, 'HEAD'), 'rb')
        self.assertEqual('ref: refs/heads/master', iter(f).next().rstrip('\n'))
        f.close()

        # ensure the symbolic link was written through
        f = open(os.path.join(self._refs.path, 'refs', 'heads', 'master'), 'rb')
        self.assertEqual(ones, f.read()[:40])
        f.close()

    def test_set_if_equals(self):
        RefsContainerTests.test_set_if_equals(self)

        # ensure symref was followed
        self.assertEqual('9' * 40, self._refs['refs/heads/master'])

        # ensure lockfile was deleted
        self.assertFalse(os.path.exists(
          os.path.join(self._refs.path, 'refs', 'heads', 'master.lock')))
        self.assertFalse(os.path.exists(
          os.path.join(self._refs.path, 'HEAD.lock')))

    def test_add_if_new_packed(self):
        # don't overwrite packed ref
        self.assertFalse(self._refs.add_if_new('refs/tags/refs-0.1', '9' * 40))
        self.assertEqual('df6800012397fb85c56e7418dd4eb9405dee075c',
                         self._refs['refs/tags/refs-0.1'])

    def test_add_if_new_symbolic(self):
        # Use an empty repo instead of the default.
        tear_down_repo(self._repo)
        repo_dir = os.path.join(tempfile.mkdtemp(), 'test')
        os.makedirs(repo_dir)
        self._repo = Repo.init(repo_dir)
        refs = self._repo.refs

        nines = '9' * 40
        self.assertEqual('ref: refs/heads/master', refs.read_ref('HEAD'))
        self.assertFalse('refs/heads/master' in refs)
        self.assertTrue(refs.add_if_new('HEAD', nines))
        self.assertEqual('ref: refs/heads/master', refs.read_ref('HEAD'))
        self.assertEqual(nines, refs['HEAD'])
        self.assertEqual(nines, refs['refs/heads/master'])
        self.assertFalse(refs.add_if_new('HEAD', '1' * 40))
        self.assertEqual(nines, refs['HEAD'])
        self.assertEqual(nines, refs['refs/heads/master'])

    def test_follow(self):
        self.assertEqual(
          ('refs/heads/master', '42d06bd4b77fed026b154d16493e5deab78f02ec'),
          self._refs._follow('HEAD'))
        self.assertEqual(
          ('refs/heads/master', '42d06bd4b77fed026b154d16493e5deab78f02ec'),
          self._refs._follow('refs/heads/master'))
        self.assertRaises(KeyError, self._refs._follow, 'refs/heads/loop')

    def test_delitem(self):
        RefsContainerTests.test_delitem(self)
        ref_file = os.path.join(self._refs.path, 'refs', 'heads', 'master')
        self.assertFalse(os.path.exists(ref_file))
        self.assertFalse('refs/heads/master' in self._refs.get_packed_refs())

    def test_delitem_symbolic(self):
        self.assertEqual('ref: refs/heads/master',
                          self._refs.read_loose_ref('HEAD'))
        del self._refs['HEAD']
        self.assertRaises(KeyError, lambda: self._refs['HEAD'])
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
                         self._refs['refs/heads/master'])
        self.assertFalse(os.path.exists(os.path.join(self._refs.path, 'HEAD')))

    def test_remove_if_equals_symref(self):
        # HEAD is a symref, so shouldn't equal its dereferenced value
        self.assertFalse(self._refs.remove_if_equals(
          'HEAD', '42d06bd4b77fed026b154d16493e5deab78f02ec'))
        self.assertTrue(self._refs.remove_if_equals(
          'refs/heads/master', '42d06bd4b77fed026b154d16493e5deab78f02ec'))
        self.assertRaises(KeyError, lambda: self._refs['refs/heads/master'])

        # HEAD is now a broken symref
        self.assertRaises(KeyError, lambda: self._refs['HEAD'])
        self.assertEqual('ref: refs/heads/master',
                          self._refs.read_loose_ref('HEAD'))

        self.assertFalse(os.path.exists(
            os.path.join(self._refs.path, 'refs', 'heads', 'master.lock')))
        self.assertFalse(os.path.exists(
            os.path.join(self._refs.path, 'HEAD.lock')))

    def test_remove_packed_without_peeled(self):
        refs_file = os.path.join(self._repo.path, 'packed-refs')
        f = GitFile(refs_file)
        refs_data = f.read()
        f.close()
        f = GitFile(refs_file, 'wb')
        f.write('\n'.join(l for l in refs_data.split('\n')
                          if not l or l[0] not in '#^'))
        f.close()
        self._repo = Repo(self._repo.path)
        refs = self._repo.refs
        self.assertTrue(refs.remove_if_equals(
          'refs/heads/packed', '42d06bd4b77fed026b154d16493e5deab78f02ec'))

    def test_remove_if_equals_packed(self):
        # test removing ref that is only packed
        self.assertEqual('df6800012397fb85c56e7418dd4eb9405dee075c',
                         self._refs['refs/tags/refs-0.1'])
        self.assertTrue(
          self._refs.remove_if_equals('refs/tags/refs-0.1',
          'df6800012397fb85c56e7418dd4eb9405dee075c'))
        self.assertRaises(KeyError, lambda: self._refs['refs/tags/refs-0.1'])

    def test_read_ref(self):
        self.assertEqual('ref: refs/heads/master', self._refs.read_ref("HEAD"))
        self.assertEqual('42d06bd4b77fed026b154d16493e5deab78f02ec',
            self._refs.read_ref("refs/heads/packed"))
        self.assertEqual(None,
            self._refs.read_ref("nonexistant"))


_TEST_REFS_SERIALIZED = (
'42d06bd4b77fed026b154d16493e5deab78f02ec\trefs/heads/40-char-ref-aaaaaaaaaaaaaaaaaa\n'
'42d06bd4b77fed026b154d16493e5deab78f02ec\trefs/heads/master\n'
'42d06bd4b77fed026b154d16493e5deab78f02ec\trefs/heads/packed\n'
'df6800012397fb85c56e7418dd4eb9405dee075c\trefs/tags/refs-0.1\n'
'3ec9c43c84ff242e3ef4a9fc5bc111fd780a76a8\trefs/tags/refs-0.2\n')


class InfoRefsContainerTests(TestCase):

    def test_invalid_refname(self):
        text = _TEST_REFS_SERIALIZED + '00' * 20 + '\trefs/stash\n'
        refs = InfoRefsContainer(StringIO(text))
        expected_refs = dict(_TEST_REFS)
        del expected_refs['HEAD']
        expected_refs["refs/stash"] = "00" * 20
        self.assertEqual(expected_refs, refs.as_dict())

    def test_keys(self):
        refs = InfoRefsContainer(StringIO(_TEST_REFS_SERIALIZED))
        actual_keys = set(refs.keys())
        self.assertEqual(set(refs.allkeys()), actual_keys)
        # ignore the symref loop if it exists
        actual_keys.discard('refs/heads/loop')
        expected_refs = dict(_TEST_REFS)
        del expected_refs['HEAD']
        self.assertEqual(set(expected_refs.iterkeys()), actual_keys)

        actual_keys = refs.keys('refs/heads')
        actual_keys.discard('loop')
        self.assertEqual(
            ['40-char-ref-aaaaaaaaaaaaaaaaaa', 'master', 'packed'],
            sorted(actual_keys))
        self.assertEqual(['refs-0.1', 'refs-0.2'],
                         sorted(refs.keys('refs/tags')))

    def test_as_dict(self):
        refs = InfoRefsContainer(StringIO(_TEST_REFS_SERIALIZED))
        # refs/heads/loop does not show up even if it exists
        expected_refs = dict(_TEST_REFS)
        del expected_refs['HEAD']
        self.assertEqual(expected_refs, refs.as_dict())

    def test_contains(self):
        refs = InfoRefsContainer(StringIO(_TEST_REFS_SERIALIZED))
        self.assertTrue('refs/heads/master' in refs)
        self.assertFalse('refs/heads/bar' in refs)

    def test_get_peeled(self):
        refs = InfoRefsContainer(StringIO(_TEST_REFS_SERIALIZED))
        # refs/heads/loop does not show up even if it exists
        self.assertEqual(
            _TEST_REFS['refs/heads/master'],
            refs.get_peeled('refs/heads/master'))

########NEW FILE########
__FILENAME__ = test_server
# test_server.py -- Tests for the git server
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for the smart protocol server."""

from cStringIO import StringIO
import os
import tempfile

from dulwich.errors import (
    GitProtocolError,
    NotGitRepository,
    UnexpectedCommandError,
    )
from dulwich.repo import (
    MemoryRepo,
    Repo,
    )
from dulwich.server import (
    Backend,
    DictBackend,
    FileSystemBackend,
    Handler,
    MultiAckGraphWalkerImpl,
    MultiAckDetailedGraphWalkerImpl,
    _split_proto_line,
    serve_command,
    ProtocolGraphWalker,
    ReceivePackHandler,
    SingleAckGraphWalkerImpl,
    UploadPackHandler,
    update_server_info,
    )
from dulwich.tests import TestCase
from dulwich.tests.utils import (
    make_commit,
    )
from dulwich.protocol import (
    ZERO_SHA,
    )

ONE = '1' * 40
TWO = '2' * 40
THREE = '3' * 40
FOUR = '4' * 40
FIVE = '5' * 40
SIX = '6' * 40


class TestProto(object):

    def __init__(self):
        self._output = []
        self._received = {0: [], 1: [], 2: [], 3: []}

    def set_output(self, output_lines):
        self._output = ['%s\n' % line.rstrip() for line in output_lines]

    def read_pkt_line(self):
        if self._output:
            return self._output.pop(0)
        else:
            return None

    def write_sideband(self, band, data):
        self._received[band].append(data)

    def write_pkt_line(self, data):
        self._received[0].append(data)

    def get_received_line(self, band=0):
        lines = self._received[band]
        return lines.pop(0)


class TestGenericHandler(Handler):

    def __init__(self):
        Handler.__init__(self, Backend(), None)

    @classmethod
    def capabilities(cls):
        return ('cap1', 'cap2', 'cap3')

    @classmethod
    def required_capabilities(cls):
        return ('cap2',)


class HandlerTestCase(TestCase):

    def setUp(self):
        super(HandlerTestCase, self).setUp()
        self._handler = TestGenericHandler()

    def assertSucceeds(self, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except GitProtocolError, e:
            self.fail(e)

    def test_capability_line(self):
        self.assertEqual('cap1 cap2 cap3', self._handler.capability_line())

    def test_set_client_capabilities(self):
        set_caps = self._handler.set_client_capabilities
        self.assertSucceeds(set_caps, ['cap2'])
        self.assertSucceeds(set_caps, ['cap1', 'cap2'])

        # different order
        self.assertSucceeds(set_caps, ['cap3', 'cap1', 'cap2'])

        # error cases
        self.assertRaises(GitProtocolError, set_caps, ['capxxx', 'cap2'])
        self.assertRaises(GitProtocolError, set_caps, ['cap1', 'cap3'])

        # ignore innocuous but unknown capabilities
        self.assertRaises(GitProtocolError, set_caps, ['cap2', 'ignoreme'])
        self.assertFalse('ignoreme' in self._handler.capabilities())
        self._handler.innocuous_capabilities = lambda: ('ignoreme',)
        self.assertSucceeds(set_caps, ['cap2', 'ignoreme'])

    def test_has_capability(self):
        self.assertRaises(GitProtocolError, self._handler.has_capability, 'cap')
        caps = self._handler.capabilities()
        self._handler.set_client_capabilities(caps)
        for cap in caps:
            self.assertTrue(self._handler.has_capability(cap))
        self.assertFalse(self._handler.has_capability('capxxx'))


class UploadPackHandlerTestCase(TestCase):

    def setUp(self):
        super(UploadPackHandlerTestCase, self).setUp()
        self._repo = MemoryRepo.init_bare([], {})
        backend = DictBackend({'/': self._repo})
        self._handler = UploadPackHandler(
          backend, ['/', 'host=lolcathost'], TestProto())

    def test_progress(self):
        caps = self._handler.required_capabilities()
        self._handler.set_client_capabilities(caps)
        self._handler.progress('first message')
        self._handler.progress('second message')
        self.assertEqual('first message',
                         self._handler.proto.get_received_line(2))
        self.assertEqual('second message',
                         self._handler.proto.get_received_line(2))
        self.assertRaises(IndexError, self._handler.proto.get_received_line, 2)

    def test_no_progress(self):
        caps = list(self._handler.required_capabilities()) + ['no-progress']
        self._handler.set_client_capabilities(caps)
        self._handler.progress('first message')
        self._handler.progress('second message')
        self.assertRaises(IndexError, self._handler.proto.get_received_line, 2)

    def test_get_tagged(self):
        refs = {
            'refs/tags/tag1': ONE,
            'refs/tags/tag2': TWO,
            'refs/heads/master': FOUR,  # not a tag, no peeled value
            }
        # repo needs to peel this object
        self._repo.object_store.add_object(make_commit(id=FOUR))
        self._repo.refs._update(refs)
        peeled = {
            'refs/tags/tag1': '1234' * 10,
            'refs/tags/tag2': '5678' * 10,
            }
        self._repo.refs._update_peeled(peeled)

        caps = list(self._handler.required_capabilities()) + ['include-tag']
        self._handler.set_client_capabilities(caps)
        self.assertEqual({'1234' * 10: ONE, '5678' * 10: TWO},
                          self._handler.get_tagged(refs, repo=self._repo))

        # non-include-tag case
        caps = self._handler.required_capabilities()
        self._handler.set_client_capabilities(caps)
        self.assertEqual({}, self._handler.get_tagged(refs, repo=self._repo))


class TestUploadPackHandler(UploadPackHandler):
    @classmethod
    def required_capabilities(self):
        return ()

class ReceivePackHandlerTestCase(TestCase):

    def setUp(self):
        super(ReceivePackHandlerTestCase, self).setUp()
        self._repo = MemoryRepo.init_bare([], {})
        backend = DictBackend({'/': self._repo})
        self._handler = ReceivePackHandler(
          backend, ['/', 'host=lolcathost'], TestProto())

    def test_apply_pack_del_ref(self):
        refs = {
            'refs/heads/master': TWO,
            'refs/heads/fake-branch': ONE}
        self._repo.refs._update(refs)
        update_refs = [[ONE, ZERO_SHA, 'refs/heads/fake-branch'], ]
        status = self._handler._apply_pack(update_refs)
        self.assertEqual(status[0][0], 'unpack')
        self.assertEqual(status[0][1], 'ok')
        self.assertEqual(status[1][0], 'refs/heads/fake-branch')
        self.assertEqual(status[1][1], 'ok')


class ProtocolGraphWalkerTestCase(TestCase):

    def setUp(self):
        super(ProtocolGraphWalkerTestCase, self).setUp()
        # Create the following commit tree:
        #   3---5
        #  /
        # 1---2---4
        commits = [
          make_commit(id=ONE, parents=[], commit_time=111),
          make_commit(id=TWO, parents=[ONE], commit_time=222),
          make_commit(id=THREE, parents=[ONE], commit_time=333),
          make_commit(id=FOUR, parents=[TWO], commit_time=444),
          make_commit(id=FIVE, parents=[THREE], commit_time=555),
          ]
        self._repo = MemoryRepo.init_bare(commits, {})
        backend = DictBackend({'/': self._repo})
        self._walker = ProtocolGraphWalker(
            TestUploadPackHandler(backend, ['/', 'host=lolcats'], TestProto()),
            self._repo.object_store, self._repo.get_peeled)

    def test_is_satisfied_no_haves(self):
        self.assertFalse(self._walker._is_satisfied([], ONE, 0))
        self.assertFalse(self._walker._is_satisfied([], TWO, 0))
        self.assertFalse(self._walker._is_satisfied([], THREE, 0))

    def test_is_satisfied_have_root(self):
        self.assertTrue(self._walker._is_satisfied([ONE], ONE, 0))
        self.assertTrue(self._walker._is_satisfied([ONE], TWO, 0))
        self.assertTrue(self._walker._is_satisfied([ONE], THREE, 0))

    def test_is_satisfied_have_branch(self):
        self.assertTrue(self._walker._is_satisfied([TWO], TWO, 0))
        # wrong branch
        self.assertFalse(self._walker._is_satisfied([TWO], THREE, 0))

    def test_all_wants_satisfied(self):
        self._walker.set_wants([FOUR, FIVE])
        # trivial case: wants == haves
        self.assertTrue(self._walker.all_wants_satisfied([FOUR, FIVE]))
        # cases that require walking the commit tree
        self.assertTrue(self._walker.all_wants_satisfied([ONE]))
        self.assertFalse(self._walker.all_wants_satisfied([TWO]))
        self.assertFalse(self._walker.all_wants_satisfied([THREE]))
        self.assertTrue(self._walker.all_wants_satisfied([TWO, THREE]))

    def test_split_proto_line(self):
        allowed = ('want', 'done', None)
        self.assertEqual(('want', ONE),
                          _split_proto_line('want %s\n' % ONE, allowed))
        self.assertEqual(('want', TWO),
                          _split_proto_line('want %s\n' % TWO, allowed))
        self.assertRaises(GitProtocolError, _split_proto_line,
                          'want xxxx\n', allowed)
        self.assertRaises(UnexpectedCommandError, _split_proto_line,
                          'have %s\n' % THREE, allowed)
        self.assertRaises(GitProtocolError, _split_proto_line,
                          'foo %s\n' % FOUR, allowed)
        self.assertRaises(GitProtocolError, _split_proto_line, 'bar', allowed)
        self.assertEqual(('done', None), _split_proto_line('done\n', allowed))
        self.assertEqual((None, None), _split_proto_line('', allowed))

    def test_determine_wants(self):
        self.assertEqual([], self._walker.determine_wants({}))
        self.assertEqual(None, self._walker.proto.get_received_line())

        self._walker.proto.set_output([
          'want %s multi_ack' % ONE,
          'want %s' % TWO,
          ])
        heads = {
          'refs/heads/ref1': ONE,
          'refs/heads/ref2': TWO,
          'refs/heads/ref3': THREE,
          }
        self._repo.refs._update(heads)
        self.assertEqual([ONE, TWO], self._walker.determine_wants(heads))

        self._walker.proto.set_output(['want %s multi_ack' % FOUR])
        self.assertRaises(GitProtocolError, self._walker.determine_wants, heads)

        self._walker.proto.set_output([])
        self.assertEqual([], self._walker.determine_wants(heads))

        self._walker.proto.set_output(['want %s multi_ack' % ONE, 'foo'])
        self.assertRaises(GitProtocolError, self._walker.determine_wants, heads)

        self._walker.proto.set_output(['want %s multi_ack' % FOUR])
        self.assertRaises(GitProtocolError, self._walker.determine_wants, heads)

    def test_determine_wants_advertisement(self):
        self._walker.proto.set_output([])
        # advertise branch tips plus tag
        heads = {
          'refs/heads/ref4': FOUR,
          'refs/heads/ref5': FIVE,
          'refs/heads/tag6': SIX,
          }
        self._repo.refs._update(heads)
        self._repo.refs._update_peeled(heads)
        self._repo.refs._update_peeled({'refs/heads/tag6': FIVE})
        self._walker.determine_wants(heads)
        lines = []
        while True:
            line = self._walker.proto.get_received_line()
            if line is None:
                break
            # strip capabilities list if present
            if '\x00' in line:
                line = line[:line.index('\x00')]
            lines.append(line.rstrip())

        self.assertEqual([
          '%s refs/heads/ref4' % FOUR,
          '%s refs/heads/ref5' % FIVE,
          '%s refs/heads/tag6^{}' % FIVE,
          '%s refs/heads/tag6' % SIX,
          ], sorted(lines))

        # ensure peeled tag was advertised immediately following tag
        for i, line in enumerate(lines):
            if line.endswith(' refs/heads/tag6'):
                self.assertEqual('%s refs/heads/tag6^{}' % FIVE, lines[i+1])

    # TODO: test commit time cutoff


class TestProtocolGraphWalker(object):

    def __init__(self):
        self.acks = []
        self.lines = []
        self.done = False
        self.http_req = None
        self.advertise_refs = False

    def read_proto_line(self, allowed):
        command, sha = self.lines.pop(0)
        if allowed is not None:
            assert command in allowed
        return command, sha

    def send_ack(self, sha, ack_type=''):
        self.acks.append((sha, ack_type))

    def send_nak(self):
        self.acks.append((None, 'nak'))

    def all_wants_satisfied(self, haves):
        return self.done

    def pop_ack(self):
        if not self.acks:
            return None
        return self.acks.pop(0)


class AckGraphWalkerImplTestCase(TestCase):
    """Base setup and asserts for AckGraphWalker tests."""

    def setUp(self):
        super(AckGraphWalkerImplTestCase, self).setUp()
        self._walker = TestProtocolGraphWalker()
        self._walker.lines = [
          ('have', TWO),
          ('have', ONE),
          ('have', THREE),
          ('done', None),
          ]
        self._impl = self.impl_cls(self._walker)

    def assertNoAck(self):
        self.assertEqual(None, self._walker.pop_ack())

    def assertAcks(self, acks):
        for sha, ack_type in acks:
            self.assertEqual((sha, ack_type), self._walker.pop_ack())
        self.assertNoAck()

    def assertAck(self, sha, ack_type=''):
        self.assertAcks([(sha, ack_type)])

    def assertNak(self):
        self.assertAck(None, 'nak')

    def assertNextEquals(self, sha):
        self.assertEqual(sha, self._impl.next())


class SingleAckGraphWalkerImplTestCase(AckGraphWalkerImplTestCase):

    impl_cls = SingleAckGraphWalkerImpl

    def test_single_ack(self):
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self._walker.done = True
        self._impl.ack(ONE)
        self.assertAck(ONE)

        self.assertNextEquals(THREE)
        self._impl.ack(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        self.assertNoAck()

    def test_single_ack_flush(self):
        # same as ack test but ends with a flush-pkt instead of done
        self._walker.lines[-1] = (None, None)

        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self._walker.done = True
        self._impl.ack(ONE)
        self.assertAck(ONE)

        self.assertNextEquals(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        self.assertNoAck()

    def test_single_ack_nak(self):
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self.assertNoAck()

        self.assertNextEquals(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        self.assertNak()

    def test_single_ack_nak_flush(self):
        # same as nak test but ends with a flush-pkt instead of done
        self._walker.lines[-1] = (None, None)

        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self.assertNoAck()

        self.assertNextEquals(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        self.assertNak()


class MultiAckGraphWalkerImplTestCase(AckGraphWalkerImplTestCase):

    impl_cls = MultiAckGraphWalkerImpl

    def test_multi_ack(self):
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self._walker.done = True
        self._impl.ack(ONE)
        self.assertAck(ONE, 'continue')

        self.assertNextEquals(THREE)
        self._impl.ack(THREE)
        self.assertAck(THREE, 'continue')

        self.assertNextEquals(None)
        self.assertAck(THREE)

    def test_multi_ack_partial(self):
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self._impl.ack(ONE)
        self.assertAck(ONE, 'continue')

        self.assertNextEquals(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        # done, re-send ack of last common
        self.assertAck(ONE)

    def test_multi_ack_flush(self):
        self._walker.lines = [
          ('have', TWO),
          (None, None),
          ('have', ONE),
          ('have', THREE),
          ('done', None),
          ]
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self.assertNak()  # nak the flush-pkt

        self._walker.done = True
        self._impl.ack(ONE)
        self.assertAck(ONE, 'continue')

        self.assertNextEquals(THREE)
        self._impl.ack(THREE)
        self.assertAck(THREE, 'continue')

        self.assertNextEquals(None)
        self.assertAck(THREE)

    def test_multi_ack_nak(self):
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self.assertNoAck()

        self.assertNextEquals(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        self.assertNak()


class MultiAckDetailedGraphWalkerImplTestCase(AckGraphWalkerImplTestCase):

    impl_cls = MultiAckDetailedGraphWalkerImpl

    def test_multi_ack(self):
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self._walker.done = True
        self._impl.ack(ONE)
        self.assertAcks([(ONE, 'common'), (ONE, 'ready')])

        self.assertNextEquals(THREE)
        self._impl.ack(THREE)
        self.assertAck(THREE, 'ready')

        self.assertNextEquals(None)
        self.assertAck(THREE)

    def test_multi_ack_partial(self):
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self._impl.ack(ONE)
        self.assertAck(ONE, 'common')

        self.assertNextEquals(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        # done, re-send ack of last common
        self.assertAck(ONE)

    def test_multi_ack_flush(self):
        # same as ack test but contains a flush-pkt in the middle
        self._walker.lines = [
          ('have', TWO),
          (None, None),
          ('have', ONE),
          ('have', THREE),
          ('done', None),
          ]
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self.assertNak()  # nak the flush-pkt

        self._walker.done = True
        self._impl.ack(ONE)
        self.assertAcks([(ONE, 'common'), (ONE, 'ready')])

        self.assertNextEquals(THREE)
        self._impl.ack(THREE)
        self.assertAck(THREE, 'ready')

        self.assertNextEquals(None)
        self.assertAck(THREE)

    def test_multi_ack_nak(self):
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self.assertNoAck()

        self.assertNextEquals(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        self.assertNak()

    def test_multi_ack_nak_flush(self):
        # same as nak test but contains a flush-pkt in the middle
        self._walker.lines = [
          ('have', TWO),
          (None, None),
          ('have', ONE),
          ('have', THREE),
          ('done', None),
          ]
        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self.assertNak()

        self.assertNextEquals(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        self.assertNak()

    def test_multi_ack_stateless(self):
        # transmission ends with a flush-pkt
        self._walker.lines[-1] = (None, None)
        self._walker.http_req = True

        self.assertNextEquals(TWO)
        self.assertNoAck()

        self.assertNextEquals(ONE)
        self.assertNoAck()

        self.assertNextEquals(THREE)
        self.assertNoAck()

        self.assertNextEquals(None)
        self.assertNak()


class FileSystemBackendTests(TestCase):
    """Tests for FileSystemBackend."""

    def setUp(self):
        super(FileSystemBackendTests, self).setUp()
        self.path = tempfile.mkdtemp()
        self.repo = Repo.init(self.path)
        self.backend = FileSystemBackend()

    def test_nonexistant(self):
        self.assertRaises(NotGitRepository,
            self.backend.open_repository, "/does/not/exist/unless/foo")

    def test_absolute(self):
        repo = self.backend.open_repository(self.path)
        self.assertEqual(repo.path, self.repo.path)

    def test_child(self):
        self.assertRaises(NotGitRepository,
            self.backend.open_repository, os.path.join(self.path, "foo"))

    def test_bad_repo_path(self):
        repo = MemoryRepo.init_bare([], {})
        backend = DictBackend({'/': repo})

        self.assertRaises(NotGitRepository,
                          lambda: backend.open_repository('/ups'))


class ServeCommandTests(TestCase):
    """Tests for serve_command."""

    def setUp(self):
        super(ServeCommandTests, self).setUp()
        self.backend = DictBackend({})

    def serve_command(self, handler_cls, args, inf, outf):
        return serve_command(handler_cls, ["test"] + args, backend=self.backend,
            inf=inf, outf=outf)

    def test_receive_pack(self):
        commit = make_commit(id=ONE, parents=[], commit_time=111)
        self.backend.repos["/"] = MemoryRepo.init_bare(
            [commit], {"refs/heads/master": commit.id})
        outf = StringIO()
        exitcode = self.serve_command(ReceivePackHandler, ["/"], StringIO("0000"), outf)
        outlines = outf.getvalue().splitlines()
        self.assertEqual(2, len(outlines))
        self.assertEqual("1111111111111111111111111111111111111111 refs/heads/master",
            outlines[0][4:].split("\x00")[0])
        self.assertEqual("0000", outlines[-1])
        self.assertEqual(0, exitcode)


class UpdateServerInfoTests(TestCase):
    """Tests for update_server_info."""

    def setUp(self):
        super(UpdateServerInfoTests, self).setUp()
        self.path = tempfile.mkdtemp()
        self.repo = Repo.init(self.path)

    def test_empty(self):
        update_server_info(self.repo)
        self.assertEqual("",
            open(os.path.join(self.path, ".git", "info", "refs"), 'r').read())
        self.assertEqual("",
            open(os.path.join(self.path, ".git", "objects", "info", "packs"), 'r').read())

    def test_simple(self):
        commit_id = self.repo.do_commit(
            message="foo",
            committer="Joe Example <joe@example.com>",
            ref="refs/heads/foo")
        update_server_info(self.repo)
        ref_text = open(os.path.join(self.path, ".git", "info", "refs"), 'r').read()
        self.assertEqual(ref_text, "%s\trefs/heads/foo\n" % commit_id)
        packs_text = open(os.path.join(self.path, ".git", "objects", "info", "packs"), 'r').read()
        self.assertEqual(packs_text, "")

########NEW FILE########
__FILENAME__ = test_utils
# test_utils.py -- Tests for git test utilities.
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License

# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.

"""Tests for git test utilities."""

from dulwich.object_store import (
    MemoryObjectStore,
    )
from dulwich.objects import (
    Blob,
    )
from dulwich.tests import (
    TestCase,
    )
from utils import (
    make_object,
    build_commit_graph,
    )


class BuildCommitGraphTest(TestCase):

    def setUp(self):
        super(BuildCommitGraphTest, self).setUp()
        self.store = MemoryObjectStore()

    def test_linear(self):
        c1, c2 = build_commit_graph(self.store, [[1], [2, 1]])
        for obj_id in [c1.id, c2.id, c1.tree, c2.tree]:
            self.assertTrue(obj_id in self.store)
        self.assertEqual([], c1.parents)
        self.assertEqual([c1.id], c2.parents)
        self.assertEqual(c1.tree, c2.tree)
        self.assertEqual([], list(self.store[c1.tree].iteritems()))
        self.assertTrue(c2.commit_time > c1.commit_time)

    def test_merge(self):
        c1, c2, c3, c4 = build_commit_graph(self.store,
                                            [[1], [2, 1], [3, 1], [4, 2, 3]])
        self.assertEqual([c2.id, c3.id], c4.parents)
        self.assertTrue(c4.commit_time > c2.commit_time)
        self.assertTrue(c4.commit_time > c3.commit_time)

    def test_missing_parent(self):
        self.assertRaises(ValueError, build_commit_graph, self.store,
                          [[1], [3, 2], [2, 1]])

    def test_trees(self):
        a1 = make_object(Blob, data='aaa1')
        a2 = make_object(Blob, data='aaa2')
        c1, c2 = build_commit_graph(self.store, [[1], [2, 1]],
                                    trees={1: [('a', a1)],
                                           2: [('a', a2, 0100644)]})
        self.assertEqual((0100644, a1.id), self.store[c1.tree]['a'])
        self.assertEqual((0100644, a2.id), self.store[c2.tree]['a'])

    def test_attrs(self):
        c1, c2 = build_commit_graph(self.store, [[1], [2, 1]],
                                    attrs={1: {'message': 'Hooray!'}})
        self.assertEqual('Hooray!', c1.message)
        self.assertEqual('Commit 2', c2.message)

    def test_commit_time(self):
        c1, c2, c3 = build_commit_graph(self.store, [[1], [2, 1], [3, 2]],
                                        attrs={1: {'commit_time': 124},
                                               2: {'commit_time': 123}})
        self.assertEqual(124, c1.commit_time)
        self.assertEqual(123, c2.commit_time)
        self.assertTrue(c2.commit_time < c1.commit_time < c3.commit_time)

########NEW FILE########
__FILENAME__ = test_walk
# test_walk.py -- Tests for commit walking functionality.
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for commit walking functionality."""

from dulwich._compat import (
    permutations,
    )
from dulwich.diff_tree import (
    CHANGE_ADD,
    CHANGE_MODIFY,
    CHANGE_RENAME,
    CHANGE_COPY,
    TreeChange,
    RenameDetector,
    )
from dulwich.errors import (
    MissingCommitError,
    )
from dulwich.object_store import (
    MemoryObjectStore,
    )
from dulwich.objects import (
    Commit,
    Blob,
    )
from dulwich.walk import (
    ORDER_TOPO,
    WalkEntry,
    Walker,
    _topo_reorder
    )
from dulwich.tests import TestCase
from utils import (
    F,
    make_object,
    build_commit_graph,
    )


class TestWalkEntry(object):

    def __init__(self, commit, changes):
        self.commit = commit
        self.changes = changes

    def __repr__(self):
        return '<TestWalkEntry commit=%s, changes=%r>' % (
          self.commit.id, self.changes)

    def __eq__(self, other):
        if not isinstance(other, WalkEntry) or self.commit != other.commit:
            return False
        if self.changes is None:
            return True
        return self.changes == other.changes()


class WalkerTest(TestCase):

    def setUp(self):
        super(WalkerTest, self).setUp()
        self.store = MemoryObjectStore()

    def make_commits(self, commit_spec, **kwargs):
        times = kwargs.pop('times', [])
        attrs = kwargs.pop('attrs', {})
        for i, t in enumerate(times):
            attrs.setdefault(i + 1, {})['commit_time'] = t
        return build_commit_graph(self.store, commit_spec, attrs=attrs,
                                  **kwargs)

    def make_linear_commits(self, num_commits, **kwargs):
        commit_spec = []
        for i in xrange(1, num_commits + 1):
            c = [i]
            if i > 1:
                c.append(i - 1)
            commit_spec.append(c)
        return self.make_commits(commit_spec, **kwargs)

    def assertWalkYields(self, expected, *args, **kwargs):
        walker = Walker(self.store, *args, **kwargs)
        expected = list(expected)
        for i, entry in enumerate(expected):
            if isinstance(entry, Commit):
                expected[i] = TestWalkEntry(entry, None)
        actual = list(walker)
        self.assertEqual(expected, actual)

    def test_linear(self):
        c1, c2, c3 = self.make_linear_commits(3)
        self.assertWalkYields([c1], [c1.id])
        self.assertWalkYields([c2, c1], [c2.id])
        self.assertWalkYields([c3, c2, c1], [c3.id])
        self.assertWalkYields([c3, c2, c1], [c3.id, c1.id])
        self.assertWalkYields([c3, c2], [c3.id], exclude=[c1.id])
        self.assertWalkYields([c3, c2], [c3.id, c1.id], exclude=[c1.id])
        self.assertWalkYields([c3], [c3.id, c1.id], exclude=[c2.id])

    def test_missing(self):
        cs = list(reversed(self.make_linear_commits(20)))
        self.assertWalkYields(cs, [cs[0].id])

        # Exactly how close we can get to a missing commit depends on our
        # implementation (in particular the choice of _MAX_EXTRA_COMMITS), but
        # we should at least be able to walk some history in a broken repo.
        del self.store[cs[-1].id]
        for i in xrange(1, 11):
            self.assertWalkYields(cs[:i], [cs[0].id], max_entries=i)
        self.assertRaises(MissingCommitError, Walker, self.store, [cs[-1].id])

    def test_branch(self):
        c1, x2, x3, y4 = self.make_commits([[1], [2, 1], [3, 2], [4, 1]])
        self.assertWalkYields([x3, x2, c1], [x3.id])
        self.assertWalkYields([y4, c1], [y4.id])
        self.assertWalkYields([y4, x2, c1], [y4.id, x2.id])
        self.assertWalkYields([y4, x2], [y4.id, x2.id], exclude=[c1.id])
        self.assertWalkYields([y4, x3], [y4.id, x3.id], exclude=[x2.id])
        self.assertWalkYields([y4], [y4.id], exclude=[x3.id])
        self.assertWalkYields([x3, x2], [x3.id], exclude=[y4.id])

    def test_merge(self):
        c1, c2, c3, c4 = self.make_commits([[1], [2, 1], [3, 1], [4, 2, 3]])
        self.assertWalkYields([c4, c3, c2, c1], [c4.id])
        self.assertWalkYields([c3, c1], [c3.id])
        self.assertWalkYields([c2, c1], [c2.id])
        self.assertWalkYields([c4, c3], [c4.id], exclude=[c2.id])
        self.assertWalkYields([c4, c2], [c4.id], exclude=[c3.id])

    def test_reverse(self):
        c1, c2, c3 = self.make_linear_commits(3)
        self.assertWalkYields([c1, c2, c3], [c3.id], reverse=True)

    def test_max_entries(self):
        c1, c2, c3 = self.make_linear_commits(3)
        self.assertWalkYields([c3, c2, c1], [c3.id], max_entries=3)
        self.assertWalkYields([c3, c2], [c3.id], max_entries=2)
        self.assertWalkYields([c3], [c3.id], max_entries=1)

    def test_reverse_after_max_entries(self):
        c1, c2, c3 = self.make_linear_commits(3)
        self.assertWalkYields([c1, c2, c3], [c3.id], max_entries=3,
                              reverse=True)
        self.assertWalkYields([c2, c3], [c3.id], max_entries=2, reverse=True)
        self.assertWalkYields([c3], [c3.id], max_entries=1, reverse=True)

    def test_changes_one_parent(self):
        blob_a1 = make_object(Blob, data='a1')
        blob_a2 = make_object(Blob, data='a2')
        blob_b2 = make_object(Blob, data='b2')
        c1, c2 = self.make_linear_commits(
          2, trees={1: [('a', blob_a1)],
                    2: [('a', blob_a2), ('b', blob_b2)]})
        e1 = TestWalkEntry(c1, [TreeChange.add(('a', F, blob_a1.id))])
        e2 = TestWalkEntry(c2, [TreeChange(CHANGE_MODIFY, ('a', F, blob_a1.id),
                                           ('a', F, blob_a2.id)),
                                TreeChange.add(('b', F, blob_b2.id))])
        self.assertWalkYields([e2, e1], [c2.id])

    def test_changes_multiple_parents(self):
        blob_a1 = make_object(Blob, data='a1')
        blob_b2 = make_object(Blob, data='b2')
        blob_a3 = make_object(Blob, data='a3')
        c1, c2, c3 = self.make_commits(
          [[1], [2], [3, 1, 2]],
          trees={1: [('a', blob_a1)], 2: [('b', blob_b2)],
                 3: [('a', blob_a3), ('b', blob_b2)]})
        # a is a modify/add conflict and b is not conflicted.
        changes = [[
          TreeChange(CHANGE_MODIFY, ('a', F, blob_a1.id), ('a', F, blob_a3.id)),
          TreeChange.add(('a', F, blob_a3.id)),
          ]]
        self.assertWalkYields([TestWalkEntry(c3, changes)], [c3.id],
                              exclude=[c1.id, c2.id])

    def test_path_matches(self):
        walker = Walker(None, [], paths=['foo', 'bar', 'baz/quux'])
        self.assertTrue(walker._path_matches('foo'))
        self.assertTrue(walker._path_matches('foo/a'))
        self.assertTrue(walker._path_matches('foo/a/b'))
        self.assertTrue(walker._path_matches('bar'))
        self.assertTrue(walker._path_matches('baz/quux'))
        self.assertTrue(walker._path_matches('baz/quux/a'))

        self.assertFalse(walker._path_matches(None))
        self.assertFalse(walker._path_matches('oops'))
        self.assertFalse(walker._path_matches('fool'))
        self.assertFalse(walker._path_matches('baz'))
        self.assertFalse(walker._path_matches('baz/quu'))

    def test_paths(self):
        blob_a1 = make_object(Blob, data='a1')
        blob_b2 = make_object(Blob, data='b2')
        blob_a3 = make_object(Blob, data='a3')
        blob_b3 = make_object(Blob, data='b3')
        c1, c2, c3 = self.make_linear_commits(
          3, trees={1: [('a', blob_a1)],
                    2: [('a', blob_a1), ('x/b', blob_b2)],
                    3: [('a', blob_a3), ('x/b', blob_b3)]})

        self.assertWalkYields([c3, c2, c1], [c3.id])
        self.assertWalkYields([c3, c1], [c3.id], paths=['a'])
        self.assertWalkYields([c3, c2], [c3.id], paths=['x/b'])

        # All changes are included, not just for requested paths.
        changes = [
          TreeChange(CHANGE_MODIFY, ('a', F, blob_a1.id),
                     ('a', F, blob_a3.id)),
          TreeChange(CHANGE_MODIFY, ('x/b', F, blob_b2.id),
                     ('x/b', F, blob_b3.id)),
          ]
        self.assertWalkYields([TestWalkEntry(c3, changes)], [c3.id],
                              max_entries=1, paths=['a'])

    def test_paths_subtree(self):
        blob_a = make_object(Blob, data='a')
        blob_b = make_object(Blob, data='b')
        c1, c2, c3 = self.make_linear_commits(
          3, trees={1: [('x/a', blob_a)],
                    2: [('b', blob_b), ('x/a', blob_a)],
                    3: [('b', blob_b), ('x/a', blob_a), ('x/b', blob_b)]})
        self.assertWalkYields([c2], [c3.id], paths=['b'])
        self.assertWalkYields([c3, c1], [c3.id], paths=['x'])

    def test_paths_max_entries(self):
        blob_a = make_object(Blob, data='a')
        blob_b = make_object(Blob, data='b')
        c1, c2 = self.make_linear_commits(
          2, trees={1: [('a', blob_a)],
                    2: [('a', blob_a), ('b', blob_b)]})
        self.assertWalkYields([c2], [c2.id], paths=['b'], max_entries=1)
        self.assertWalkYields([c1], [c1.id], paths=['a'], max_entries=1)

    def test_paths_merge(self):
        blob_a1 = make_object(Blob, data='a1')
        blob_a2 = make_object(Blob, data='a2')
        blob_a3 = make_object(Blob, data='a3')
        x1, y2, m3, m4 = self.make_commits(
          [[1], [2], [3, 1, 2], [4, 1, 2]],
          trees={1: [('a', blob_a1)],
                 2: [('a', blob_a2)],
                 3: [('a', blob_a3)],
                 4: [('a', blob_a1)]})  # Non-conflicting
        self.assertWalkYields([m3, y2, x1], [m3.id], paths=['a'])
        self.assertWalkYields([y2, x1], [m4.id], paths=['a'])

    def test_changes_with_renames(self):
        blob = make_object(Blob, data='blob')
        c1, c2 = self.make_linear_commits(
          2, trees={1: [('a', blob)], 2: [('b', blob)]})
        entry_a = ('a', F, blob.id)
        entry_b = ('b', F, blob.id)
        changes_without_renames = [TreeChange.delete(entry_a),
                                   TreeChange.add(entry_b)]
        changes_with_renames = [TreeChange(CHANGE_RENAME, entry_a, entry_b)]
        self.assertWalkYields(
          [TestWalkEntry(c2, changes_without_renames)], [c2.id], max_entries=1)
        detector = RenameDetector(self.store)
        self.assertWalkYields(
          [TestWalkEntry(c2, changes_with_renames)], [c2.id], max_entries=1,
          rename_detector=detector)

    def test_follow_rename(self):
        blob = make_object(Blob, data='blob')
        names = ['a', 'a', 'b', 'b', 'c', 'c']

        trees = dict((i + 1, [(n, blob, F)]) for i, n in enumerate(names))
        c1, c2, c3, c4, c5, c6 = self.make_linear_commits(6, trees=trees)
        self.assertWalkYields([c5], [c6.id], paths=['c'])

        e = lambda n: (n, F, blob.id)
        self.assertWalkYields(
          [TestWalkEntry(c5, [TreeChange(CHANGE_RENAME, e('b'), e('c'))]),
           TestWalkEntry(c3, [TreeChange(CHANGE_RENAME, e('a'), e('b'))]),
           TestWalkEntry(c1, [TreeChange.add(e('a'))])],
          [c6.id], paths=['c'], follow=True)

    def test_follow_rename_remove_path(self):
        blob = make_object(Blob, data='blob')
        _, _, _, c4, c5, c6 = self.make_linear_commits(
          6, trees={1: [('a', blob), ('c', blob)],
                    2: [],
                    3: [],
                    4: [('b', blob)],
                    5: [('a', blob)],
                    6: [('c', blob)]})

        e = lambda n: (n, F, blob.id)
        # Once the path changes to b, we aren't interested in a or c anymore.
        self.assertWalkYields(
          [TestWalkEntry(c6, [TreeChange(CHANGE_RENAME, e('a'), e('c'))]),
           TestWalkEntry(c5, [TreeChange(CHANGE_RENAME, e('b'), e('a'))]),
           TestWalkEntry(c4, [TreeChange.add(e('b'))])],
          [c6.id], paths=['c'], follow=True)

    def test_since(self):
        c1, c2, c3 = self.make_linear_commits(3)
        self.assertWalkYields([c3, c2, c1], [c3.id], since=-1)
        self.assertWalkYields([c3, c2, c1], [c3.id], since=0)
        self.assertWalkYields([c3, c2], [c3.id], since=1)
        self.assertWalkYields([c3, c2], [c3.id], since=99)
        self.assertWalkYields([c3, c2], [c3.id], since=100)
        self.assertWalkYields([c3], [c3.id], since=101)
        self.assertWalkYields([c3], [c3.id], since=199)
        self.assertWalkYields([c3], [c3.id], since=200)
        self.assertWalkYields([], [c3.id], since=201)
        self.assertWalkYields([], [c3.id], since=300)

    def test_until(self):
        c1, c2, c3 = self.make_linear_commits(3)
        self.assertWalkYields([], [c3.id], until=-1)
        self.assertWalkYields([c1], [c3.id], until=0)
        self.assertWalkYields([c1], [c3.id], until=1)
        self.assertWalkYields([c1], [c3.id], until=99)
        self.assertWalkYields([c2, c1], [c3.id], until=100)
        self.assertWalkYields([c2, c1], [c3.id], until=101)
        self.assertWalkYields([c2, c1], [c3.id], until=199)
        self.assertWalkYields([c3, c2, c1], [c3.id], until=200)
        self.assertWalkYields([c3, c2, c1], [c3.id], until=201)
        self.assertWalkYields([c3, c2, c1], [c3.id], until=300)

    def test_since_until(self):
        c1, c2, c3 = self.make_linear_commits(3)
        self.assertWalkYields([], [c3.id], since=100, until=99)
        self.assertWalkYields([c3, c2, c1], [c3.id], since=-1, until=201)
        self.assertWalkYields([c2], [c3.id], since=100, until=100)
        self.assertWalkYields([c2], [c3.id], since=50, until=150)

    def test_since_over_scan(self):
        commits = self.make_linear_commits(
          11, times=[9, 0, 1, 2, 3, 4, 5, 8, 6, 7, 9])
        c8, _, c10, c11 = commits[-4:]
        del self.store[commits[0].id]
        # c9 is older than we want to walk, but is out of order with its parent,
        # so we need to walk past it to get to c8.
        # c1 would also match, but we've deleted it, and it should get pruned
        # even with over-scanning.
        self.assertWalkYields([c11, c10, c8], [c11.id], since=7)

    def assertTopoOrderEqual(self, expected_commits, commits):
        entries = [TestWalkEntry(c, None) for c in commits]
        actual_ids = [e.commit.id for e in list(_topo_reorder(entries))]
        self.assertEqual([c.id for c in expected_commits], actual_ids)

    def test_topo_reorder_linear(self):
        commits = self.make_linear_commits(5)
        commits.reverse()
        for perm in permutations(commits):
            self.assertTopoOrderEqual(commits, perm)

    def test_topo_reorder_multiple_parents(self):
        c1, c2, c3 = self.make_commits([[1], [2], [3, 1, 2]])
        # Already sorted, so totally FIFO.
        self.assertTopoOrderEqual([c3, c2, c1], [c3, c2, c1])
        self.assertTopoOrderEqual([c3, c1, c2], [c3, c1, c2])

        # c3 causes one parent to be yielded.
        self.assertTopoOrderEqual([c3, c2, c1], [c2, c3, c1])
        self.assertTopoOrderEqual([c3, c1, c2], [c1, c3, c2])

        # c3 causes both parents to be yielded.
        self.assertTopoOrderEqual([c3, c2, c1], [c1, c2, c3])
        self.assertTopoOrderEqual([c3, c2, c1], [c2, c1, c3])

    def test_topo_reorder_multiple_children(self):
        c1, c2, c3 = self.make_commits([[1], [2, 1], [3, 1]])

        # c2 and c3 are FIFO but c1 moves to the end.
        self.assertTopoOrderEqual([c3, c2, c1], [c3, c2, c1])
        self.assertTopoOrderEqual([c3, c2, c1], [c3, c1, c2])
        self.assertTopoOrderEqual([c3, c2, c1], [c1, c3, c2])

        self.assertTopoOrderEqual([c2, c3, c1], [c2, c3, c1])
        self.assertTopoOrderEqual([c2, c3, c1], [c2, c1, c3])
        self.assertTopoOrderEqual([c2, c3, c1], [c1, c2, c3])

    def test_out_of_order_children(self):
        c1, c2, c3, c4, c5 = self.make_commits(
          [[1], [2, 1], [3, 2], [4, 1], [5, 3, 4]],
          times=[2, 1, 3, 4, 5])
        self.assertWalkYields([c5, c4, c3, c1, c2], [c5.id])
        self.assertWalkYields([c5, c4, c3, c2, c1], [c5.id], order=ORDER_TOPO)

    def test_out_of_order_with_exclude(self):
        # Create the following graph:
        # c1-------x2---m6
        #   \          /
        #    \-y3--y4-/--y5
        # Due to skew, y5 is the oldest commit.
        c1, x2, y3, y4, y5, m6 = cs = self.make_commits(
          [[1], [2, 1], [3, 1], [4, 3], [5, 4], [6, 2, 4]],
          times=[2, 3, 4, 5, 1, 6])
        self.assertWalkYields([m6, y4, y3, x2, c1], [m6.id])
        # Ensure that c1..y4 get excluded even though they're popped from the
        # priority queue long before y5.
        self.assertWalkYields([m6, x2], [m6.id], exclude=[y5.id])

    def test_empty_walk(self):
        c1, c2, c3 = self.make_linear_commits(3)
        self.assertWalkYields([], [c3.id], exclude=[c3.id])

########NEW FILE########
__FILENAME__ = test_web
# test_web.py -- Tests for the git HTTP server
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Tests for the Git HTTP server."""

from cStringIO import StringIO
import gzip
import re
import os

from dulwich.object_store import (
    MemoryObjectStore,
    )
from dulwich.objects import (
    Blob,
    Tag,
    )
from dulwich.repo import (
    BaseRepo,
    MemoryRepo,
    )
from dulwich.server import (
    DictBackend,
    )
from dulwich.tests import (
    TestCase,
    )
from dulwich.web import (
    HTTP_OK,
    HTTP_NOT_FOUND,
    HTTP_FORBIDDEN,
    HTTP_ERROR,
    GunzipFilter,
    send_file,
    get_text_file,
    get_loose_object,
    get_pack_file,
    get_idx_file,
    get_info_refs,
    get_info_packs,
    handle_service_request,
    _LengthLimitedFile,
    HTTPGitRequest,
    HTTPGitApplication,
    )

from dulwich.tests.utils import (
    make_object,
    )


class TestHTTPGitRequest(HTTPGitRequest):
    """HTTPGitRequest with overridden methods to help test caching."""

    def __init__(self, *args, **kwargs):
        HTTPGitRequest.__init__(self, *args, **kwargs)
        self.cached = None

    def nocache(self):
        self.cached = False

    def cache_forever(self):
        self.cached = True


class WebTestCase(TestCase):
    """Base TestCase with useful instance vars and utility functions."""

    _req_class = TestHTTPGitRequest

    def setUp(self):
        super(WebTestCase, self).setUp()
        self._environ = {}
        self._req = self._req_class(self._environ, self._start_response,
                                    handlers=self._handlers())
        self._status = None
        self._headers = []
        self._output = StringIO()

    def _start_response(self, status, headers):
        self._status = status
        self._headers = list(headers)
        return self._output.write

    def _handlers(self):
        return None

    def assertContentTypeEquals(self, expected):
        self.assertTrue(('Content-Type', expected) in self._headers)


def _test_backend(objects, refs=None, named_files=None):
    if not refs:
        refs = {}
    if not named_files:
        named_files = {}
    repo = MemoryRepo.init_bare(objects, refs)
    for path, contents in named_files.iteritems():
        repo._put_named_file(path, contents)
    return DictBackend({'/': repo})


class DumbHandlersTestCase(WebTestCase):

    def test_send_file_not_found(self):
        list(send_file(self._req, None, 'text/plain'))
        self.assertEqual(HTTP_NOT_FOUND, self._status)

    def test_send_file(self):
        f = StringIO('foobar')
        output = ''.join(send_file(self._req, f, 'some/thing'))
        self.assertEqual('foobar', output)
        self.assertEqual(HTTP_OK, self._status)
        self.assertContentTypeEquals('some/thing')
        self.assertTrue(f.closed)

    def test_send_file_buffered(self):
        bufsize = 10240
        xs = 'x' * bufsize
        f = StringIO(2 * xs)
        self.assertEqual([xs, xs],
                          list(send_file(self._req, f, 'some/thing')))
        self.assertEqual(HTTP_OK, self._status)
        self.assertContentTypeEquals('some/thing')
        self.assertTrue(f.closed)

    def test_send_file_error(self):
        class TestFile(object):
            def __init__(self, exc_class):
                self.closed = False
                self._exc_class = exc_class

            def read(self, size=-1):
                raise self._exc_class()

            def close(self):
                self.closed = True

        f = TestFile(IOError)
        list(send_file(self._req, f, 'some/thing'))
        self.assertEqual(HTTP_ERROR, self._status)
        self.assertTrue(f.closed)
        self.assertFalse(self._req.cached)

        # non-IOErrors are reraised
        f = TestFile(AttributeError)
        self.assertRaises(AttributeError, list,
                          send_file(self._req, f, 'some/thing'))
        self.assertTrue(f.closed)
        self.assertFalse(self._req.cached)

    def test_get_text_file(self):
        backend = _test_backend([], named_files={'description': 'foo'})
        mat = re.search('.*', 'description')
        output = ''.join(get_text_file(self._req, backend, mat))
        self.assertEqual('foo', output)
        self.assertEqual(HTTP_OK, self._status)
        self.assertContentTypeEquals('text/plain')
        self.assertFalse(self._req.cached)

    def test_get_loose_object(self):
        blob = make_object(Blob, data='foo')
        backend = _test_backend([blob])
        mat = re.search('^(..)(.{38})$', blob.id)
        output = ''.join(get_loose_object(self._req, backend, mat))
        self.assertEqual(blob.as_legacy_object(), output)
        self.assertEqual(HTTP_OK, self._status)
        self.assertContentTypeEquals('application/x-git-loose-object')
        self.assertTrue(self._req.cached)

    def test_get_loose_object_missing(self):
        mat = re.search('^(..)(.{38})$', '1' * 40)
        list(get_loose_object(self._req, _test_backend([]), mat))
        self.assertEqual(HTTP_NOT_FOUND, self._status)

    def test_get_loose_object_error(self):
        blob = make_object(Blob, data='foo')
        backend = _test_backend([blob])
        mat = re.search('^(..)(.{38})$', blob.id)

        def as_legacy_object_error():
            raise IOError

        blob.as_legacy_object = as_legacy_object_error
        list(get_loose_object(self._req, backend, mat))
        self.assertEqual(HTTP_ERROR, self._status)

    def test_get_pack_file(self):
        pack_name = os.path.join('objects', 'pack', 'pack-%s.pack' % ('1' * 40))
        backend = _test_backend([], named_files={pack_name: 'pack contents'})
        mat = re.search('.*', pack_name)
        output = ''.join(get_pack_file(self._req, backend, mat))
        self.assertEqual('pack contents', output)
        self.assertEqual(HTTP_OK, self._status)
        self.assertContentTypeEquals('application/x-git-packed-objects')
        self.assertTrue(self._req.cached)

    def test_get_idx_file(self):
        idx_name = os.path.join('objects', 'pack', 'pack-%s.idx' % ('1' * 40))
        backend = _test_backend([], named_files={idx_name: 'idx contents'})
        mat = re.search('.*', idx_name)
        output = ''.join(get_idx_file(self._req, backend, mat))
        self.assertEqual('idx contents', output)
        self.assertEqual(HTTP_OK, self._status)
        self.assertContentTypeEquals('application/x-git-packed-objects-toc')
        self.assertTrue(self._req.cached)

    def test_get_info_refs(self):
        self._environ['QUERY_STRING'] = ''

        blob1 = make_object(Blob, data='1')
        blob2 = make_object(Blob, data='2')
        blob3 = make_object(Blob, data='3')

        tag1 = make_object(Tag, name='tag-tag',
                           tagger='Test <test@example.com>',
                           tag_time=12345,
                           tag_timezone=0,
                           message='message',
                           object=(Blob, blob2.id))

        objects = [blob1, blob2, blob3, tag1]
        refs = {
          'HEAD': '000',
          'refs/heads/master': blob1.id,
          'refs/tags/tag-tag': tag1.id,
          'refs/tags/blob-tag': blob3.id,
          }
        backend = _test_backend(objects, refs=refs)

        mat = re.search('.*', '//info/refs')
        self.assertEqual(['%s\trefs/heads/master\n' % blob1.id,
                           '%s\trefs/tags/blob-tag\n' % blob3.id,
                           '%s\trefs/tags/tag-tag\n' % tag1.id,
                           '%s\trefs/tags/tag-tag^{}\n' % blob2.id],
                          list(get_info_refs(self._req, backend, mat)))
        self.assertEqual(HTTP_OK, self._status)
        self.assertContentTypeEquals('text/plain')
        self.assertFalse(self._req.cached)

    def test_get_info_packs(self):
        class TestPack(object):
            def __init__(self, sha):
                self._sha = sha

            def name(self):
                return self._sha

        packs = [TestPack(str(i) * 40) for i in xrange(1, 4)]

        class TestObjectStore(MemoryObjectStore):
            # property must be overridden, can't be assigned
            @property
            def packs(self):
                return packs

        store = TestObjectStore()
        repo = BaseRepo(store, None)
        backend = DictBackend({'/': repo})
        mat = re.search('.*', '//info/packs')
        output = ''.join(get_info_packs(self._req, backend, mat))
        expected = 'P pack-%s.pack\n' * 3
        expected %= ('1' * 40, '2' * 40, '3' * 40)
        self.assertEqual(expected, output)
        self.assertEqual(HTTP_OK, self._status)
        self.assertContentTypeEquals('text/plain')
        self.assertFalse(self._req.cached)


class SmartHandlersTestCase(WebTestCase):

    class _TestUploadPackHandler(object):
        def __init__(self, backend, args, proto, http_req=None,
                     advertise_refs=False):
            self.args = args
            self.proto = proto
            self.http_req = http_req
            self.advertise_refs = advertise_refs

        def handle(self):
            self.proto.write('handled input: %s' % self.proto.recv(1024))

    def _make_handler(self, *args, **kwargs):
        self._handler = self._TestUploadPackHandler(*args, **kwargs)
        return self._handler

    def _handlers(self):
        return {'git-upload-pack': self._make_handler}

    def test_handle_service_request_unknown(self):
        mat = re.search('.*', '/git-evil-handler')
        list(handle_service_request(self._req, 'backend', mat))
        self.assertEqual(HTTP_FORBIDDEN, self._status)
        self.assertFalse(self._req.cached)

    def _run_handle_service_request(self, content_length=None):
        self._environ['wsgi.input'] = StringIO('foo')
        if content_length is not None:
            self._environ['CONTENT_LENGTH'] = content_length
        mat = re.search('.*', '/git-upload-pack')
        handler_output = ''.join(
          handle_service_request(self._req, 'backend', mat))
        write_output = self._output.getvalue()
        # Ensure all output was written via the write callback.
        self.assertEqual('', handler_output)
        self.assertEqual('handled input: foo', write_output)
        self.assertContentTypeEquals('application/x-git-upload-pack-result')
        self.assertFalse(self._handler.advertise_refs)
        self.assertTrue(self._handler.http_req)
        self.assertFalse(self._req.cached)

    def test_handle_service_request(self):
        self._run_handle_service_request()

    def test_handle_service_request_with_length(self):
        self._run_handle_service_request(content_length='3')

    def test_handle_service_request_empty_length(self):
        self._run_handle_service_request(content_length='')

    def test_get_info_refs_unknown(self):
        self._environ['QUERY_STRING'] = 'service=git-evil-handler'
        list(get_info_refs(self._req, 'backend', None))
        self.assertEqual(HTTP_FORBIDDEN, self._status)
        self.assertFalse(self._req.cached)

    def test_get_info_refs(self):
        self._environ['wsgi.input'] = StringIO('foo')
        self._environ['QUERY_STRING'] = 'service=git-upload-pack'

        mat = re.search('.*', '/git-upload-pack')
        handler_output = ''.join(get_info_refs(self._req, 'backend', mat))
        write_output = self._output.getvalue()
        self.assertEqual(('001e# service=git-upload-pack\n'
                           '0000'
                           # input is ignored by the handler
                           'handled input: '), write_output)
        # Ensure all output was written via the write callback.
        self.assertEqual('', handler_output)
        self.assertTrue(self._handler.advertise_refs)
        self.assertTrue(self._handler.http_req)
        self.assertFalse(self._req.cached)


class LengthLimitedFileTestCase(TestCase):
    def test_no_cutoff(self):
        f = _LengthLimitedFile(StringIO('foobar'), 1024)
        self.assertEqual('foobar', f.read())

    def test_cutoff(self):
        f = _LengthLimitedFile(StringIO('foobar'), 3)
        self.assertEqual('foo', f.read())
        self.assertEqual('', f.read())

    def test_multiple_reads(self):
        f = _LengthLimitedFile(StringIO('foobar'), 3)
        self.assertEqual('fo', f.read(2))
        self.assertEqual('o', f.read(2))
        self.assertEqual('', f.read())


class HTTPGitRequestTestCase(WebTestCase):

    # This class tests the contents of the actual cache headers
    _req_class = HTTPGitRequest

    def test_not_found(self):
        self._req.cache_forever()  # cache headers should be discarded
        message = 'Something not found'
        self.assertEqual(message, self._req.not_found(message))
        self.assertEqual(HTTP_NOT_FOUND, self._status)
        self.assertEqual(set([('Content-Type', 'text/plain')]),
                          set(self._headers))

    def test_forbidden(self):
        self._req.cache_forever()  # cache headers should be discarded
        message = 'Something not found'
        self.assertEqual(message, self._req.forbidden(message))
        self.assertEqual(HTTP_FORBIDDEN, self._status)
        self.assertEqual(set([('Content-Type', 'text/plain')]),
                          set(self._headers))

    def test_respond_ok(self):
        self._req.respond()
        self.assertEqual([], self._headers)
        self.assertEqual(HTTP_OK, self._status)

    def test_respond(self):
        self._req.nocache()
        self._req.respond(status=402, content_type='some/type',
                          headers=[('X-Foo', 'foo'), ('X-Bar', 'bar')])
        self.assertEqual(set([
          ('X-Foo', 'foo'),
          ('X-Bar', 'bar'),
          ('Content-Type', 'some/type'),
          ('Expires', 'Fri, 01 Jan 1980 00:00:00 GMT'),
          ('Pragma', 'no-cache'),
          ('Cache-Control', 'no-cache, max-age=0, must-revalidate'),
          ]), set(self._headers))
        self.assertEqual(402, self._status)


class HTTPGitApplicationTestCase(TestCase):

    def setUp(self):
        super(HTTPGitApplicationTestCase, self).setUp()
        self._app = HTTPGitApplication('backend')

        self._environ = {
            'PATH_INFO': '/foo',
            'REQUEST_METHOD': 'GET',
        }

    def _test_handler(self, req, backend, mat):
        # tests interface used by all handlers
        self.assertEqual(self._environ, req.environ)
        self.assertEqual('backend', backend)
        self.assertEqual('/foo', mat.group(0))
        return 'output'

    def _add_handler(self, app):
        req = self._environ['REQUEST_METHOD']
        app.services = {
          (req, re.compile('/foo$')): self._test_handler,
        }

    def test_call(self):
        self._add_handler(self._app)
        self.assertEqual('output', self._app(self._environ, None))

    def test_fallback_app(self):
        def test_app(environ, start_response):
            return 'output'

        app = HTTPGitApplication('backend', fallback_app=test_app)
        self.assertEqual('output', app(self._environ, None))


class GunzipTestCase(HTTPGitApplicationTestCase):
    """TestCase for testing the GunzipFilter, ensuring the wsgi.input
    is correctly decompressed and headers are corrected.
    """

    def setUp(self):
        super(GunzipTestCase, self).setUp()
        self._app = GunzipFilter(self._app)
        self._environ['HTTP_CONTENT_ENCODING'] = 'gzip'
        self._environ['REQUEST_METHOD'] = 'POST'

    def _get_zstream(self, text):
        zstream = StringIO()
        zfile = gzip.GzipFile(fileobj=zstream, mode='w')
        zfile.write(text)
        zfile.close()
        return zstream

    def test_call(self):
        self._add_handler(self._app.app)
        orig = self.__class__.__doc__
        zstream = self._get_zstream(orig)
        zlength = zstream.tell()
        zstream.seek(0)
        self.assertLess(zlength, len(orig))
        self.assertEqual(self._environ['HTTP_CONTENT_ENCODING'], 'gzip')
        self._environ['CONTENT_LENGTH'] = zlength
        self._environ['wsgi.input'] = zstream
        app_output = self._app(self._environ, None)
        buf = self._environ['wsgi.input']
        self.assertIsNot(buf, zstream)
        buf.seek(0)
        self.assertEqual(orig, buf.read())
        self.assertIs(None, self._environ.get('CONTENT_LENGTH'))
        self.assertNotIn('HTTP_CONTENT_ENCODING', self._environ)

########NEW FILE########
__FILENAME__ = utils
# utils.py -- Test utilities for Dulwich.
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Utility functions common to Dulwich tests."""


import datetime
import os
import shutil
import tempfile
import time
import types
import warnings

from dulwich.index import (
    commit_tree,
    )
from dulwich.objects import (
    FixedSha,
    Commit,
    )
from dulwich.pack import (
    OFS_DELTA,
    REF_DELTA,
    DELTA_TYPES,
    obj_sha,
    SHA1Writer,
    write_pack_header,
    write_pack_object,
    create_delta,
    )
from dulwich.repo import Repo
from dulwich.tests import (
    SkipTest,
    )

# Plain files are very frequently used in tests, so let the mode be very short.
F = 0100644  # Shorthand mode for Files.


def open_repo(name):
    """Open a copy of a repo in a temporary directory.

    Use this function for accessing repos in dulwich/tests/data/repos to avoid
    accidentally or intentionally modifying those repos in place. Use
    tear_down_repo to delete any temp files created.

    :param name: The name of the repository, relative to
        dulwich/tests/data/repos
    :returns: An initialized Repo object that lives in a temporary directory.
    """
    temp_dir = tempfile.mkdtemp()
    repo_dir = os.path.join(os.path.dirname(__file__), 'data', 'repos', name)
    temp_repo_dir = os.path.join(temp_dir, name)
    shutil.copytree(repo_dir, temp_repo_dir, symlinks=True)
    return Repo(temp_repo_dir)


def tear_down_repo(repo):
    """Tear down a test repository."""
    temp_dir = os.path.dirname(repo.path.rstrip(os.sep))
    shutil.rmtree(temp_dir)


def make_object(cls, **attrs):
    """Make an object for testing and assign some members.

    This method creates a new subclass to allow arbitrary attribute
    reassignment, which is not otherwise possible with objects having __slots__.

    :param attrs: dict of attributes to set on the new object.
    :return: A newly initialized object of type cls.
    """

    class TestObject(cls):
        """Class that inherits from the given class, but without __slots__.

        Note that classes with __slots__ can't have arbitrary attributes monkey-
        patched in, so this is a class that is exactly the same only with a
        __dict__ instead of __slots__.
        """
        pass

    obj = TestObject()
    for name, value in attrs.iteritems():
        if name == 'id':
            # id property is read-only, so we overwrite sha instead.
            sha = FixedSha(value)
            obj.sha = lambda: sha
        else:
            setattr(obj, name, value)
    return obj


def make_commit(**attrs):
    """Make a Commit object with a default set of members.

    :param attrs: dict of attributes to overwrite from the default values.
    :return: A newly initialized Commit object.
    """
    default_time = int(time.mktime(datetime.datetime(2010, 1, 1).timetuple()))
    all_attrs = {'author': 'Test Author <test@nodomain.com>',
                 'author_time': default_time,
                 'author_timezone': 0,
                 'committer': 'Test Committer <test@nodomain.com>',
                 'commit_time': default_time,
                 'commit_timezone': 0,
                 'message': 'Test message.',
                 'parents': [],
                 'tree': '0' * 40}
    all_attrs.update(attrs)
    return make_object(Commit, **all_attrs)


def functest_builder(method, func):
    """Generate a test method that tests the given function."""

    def do_test(self):
        method(self, func)

    return do_test


def ext_functest_builder(method, func):
    """Generate a test method that tests the given extension function.

    This is intended to generate test methods that test both a pure-Python
    version and an extension version using common test code. The extension test
    will raise SkipTest if the extension is not found.

    Sample usage:

    class MyTest(TestCase);
        def _do_some_test(self, func_impl):
            self.assertEqual('foo', func_impl())

        test_foo = functest_builder(_do_some_test, foo_py)
        test_foo_extension = ext_functest_builder(_do_some_test, _foo_c)

    :param method: The method to run. It must must two parameters, self and the
        function implementation to test.
    :param func: The function implementation to pass to method.
    """

    def do_test(self):
        if not isinstance(func, types.BuiltinFunctionType):
            raise SkipTest("%s extension not found" % func.func_name)
        method(self, func)

    return do_test


def build_pack(f, objects_spec, store=None):
    """Write test pack data from a concise spec.

    :param f: A file-like object to write the pack to.
    :param objects_spec: A list of (type_num, obj). For non-delta types, obj
        is the string of that object's data.
        For delta types, obj is a tuple of (base, data), where:

        * base can be either an index in objects_spec of the base for that
        * delta; or for a ref delta, a SHA, in which case the resulting pack
        * will be thin and the base will be an external ref.
        * data is a string of the full, non-deltified data for that object.

        Note that offsets/refs and deltas are computed within this function.
    :param store: An optional ObjectStore for looking up external refs.
    :return: A list of tuples in the order specified by objects_spec:
        (offset, type num, data, sha, CRC32)
    """
    sf = SHA1Writer(f)
    num_objects = len(objects_spec)
    write_pack_header(sf, num_objects)

    full_objects = {}
    offsets = {}
    crc32s = {}

    while len(full_objects) < num_objects:
        for i, (type_num, data) in enumerate(objects_spec):
            if type_num not in DELTA_TYPES:
                full_objects[i] = (type_num, data,
                                   obj_sha(type_num, [data]))
                continue
            base, data = data
            if isinstance(base, int):
                if base not in full_objects:
                    continue
                base_type_num, _, _ = full_objects[base]
            else:
                base_type_num, _ = store.get_raw(base)
            full_objects[i] = (base_type_num, data,
                               obj_sha(base_type_num, [data]))

    for i, (type_num, obj) in enumerate(objects_spec):
        offset = f.tell()
        if type_num == OFS_DELTA:
            base_index, data = obj
            base = offset - offsets[base_index]
            _, base_data, _ = full_objects[base_index]
            obj = (base, create_delta(base_data, data))
        elif type_num == REF_DELTA:
            base_ref, data = obj
            if isinstance(base_ref, int):
                _, base_data, base = full_objects[base_ref]
            else:
                base_type_num, base_data = store.get_raw(base_ref)
                base = obj_sha(base_type_num, base_data)
            obj = (base, create_delta(base_data, data))

        crc32 = write_pack_object(sf, type_num, obj)
        offsets[i] = offset
        crc32s[i] = crc32

    expected = []
    for i in xrange(num_objects):
        type_num, data, sha = full_objects[i]
        assert len(sha) == 20
        expected.append((offsets[i], type_num, data, sha, crc32s[i]))

    sf.write_sha()
    f.seek(0)
    return expected


def build_commit_graph(object_store, commit_spec, trees=None, attrs=None):
    """Build a commit graph from a concise specification.

    Sample usage:
    >>> c1, c2, c3 = build_commit_graph(store, [[1], [2, 1], [3, 1, 2]])
    >>> store[store[c3].parents[0]] == c1
    True
    >>> store[store[c3].parents[1]] == c2
    True

    If not otherwise specified, commits will refer to the empty tree and have
    commit times increasing in the same order as the commit spec.

    :param object_store: An ObjectStore to commit objects to.
    :param commit_spec: An iterable of iterables of ints defining the commit
        graph. Each entry defines one commit, and entries must be in topological
        order. The first element of each entry is a commit number, and the
        remaining elements are its parents. The commit numbers are only
        meaningful for the call to make_commits; since real commit objects are
        created, they will get created with real, opaque SHAs.
    :param trees: An optional dict of commit number -> tree spec for building
        trees for commits. The tree spec is an iterable of (path, blob, mode) or
        (path, blob) entries; if mode is omitted, it defaults to the normal file
        mode (0100644).
    :param attrs: A dict of commit number -> (dict of attribute -> value) for
        assigning additional values to the commits.
    :return: The list of commit objects created.
    :raise ValueError: If an undefined commit identifier is listed as a parent.
    """
    if trees is None:
        trees = {}
    if attrs is None:
        attrs = {}
    commit_time = 0
    nums = {}
    commits = []

    for commit in commit_spec:
        commit_num = commit[0]
        try:
            parent_ids = [nums[pn] for pn in commit[1:]]
        except KeyError, e:
            missing_parent, = e.args
            raise ValueError('Unknown parent %i' % missing_parent)

        blobs = []
        for entry in trees.get(commit_num, []):
            if len(entry) == 2:
                path, blob = entry
                entry = (path, blob, F)
            path, blob, mode = entry
            blobs.append((path, blob.id, mode))
            object_store.add_object(blob)
        tree_id = commit_tree(object_store, blobs)

        commit_attrs = {
            'message': 'Commit %i' % commit_num,
            'parents': parent_ids,
            'tree': tree_id,
            'commit_time': commit_time,
            }
        commit_attrs.update(attrs.get(commit_num, {}))
        commit_obj = make_commit(**commit_attrs)

        # By default, increment the time by a lot. Out-of-order commits should
        # be closer together than this because their main cause is clock skew.
        commit_time = commit_attrs['commit_time'] + 100
        nums[commit_num] = commit_obj.id
        object_store.add_object(commit_obj)
        commits.append(commit_obj)

    return commits


def setup_warning_catcher():
    """Wrap warnings.showwarning with code that records warnings."""

    caught_warnings = []
    original_showwarning = warnings.showwarning

    def custom_showwarning(*args,  **kwargs):
        caught_warnings.append(args[0])

    warnings.showwarning = custom_showwarning
    return caught_warnings

########NEW FILE########
__FILENAME__ = walk
# walk.py -- General implementation of walking commits and their contents.
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""General implementation of walking commits and their contents."""


try:
    from collections import defaultdict
except ImportError:
    from _compat import defaultdict

import collections
import heapq
import itertools

from dulwich._compat import (
    all,
    )
from dulwich.diff_tree import (
    RENAME_CHANGE_TYPES,
    tree_changes,
    tree_changes_for_merge,
    RenameDetector,
    )
from dulwich.errors import (
    MissingCommitError,
    )

ORDER_DATE = 'date'
ORDER_TOPO = 'topo'

ALL_ORDERS = (ORDER_DATE, ORDER_TOPO)

# Maximum number of commits to walk past a commit time boundary.
_MAX_EXTRA_COMMITS = 5


class WalkEntry(object):
    """Object encapsulating a single result from a walk."""

    def __init__(self, walker, commit):
        self.commit = commit
        self._store = walker.store
        self._changes = None
        self._rename_detector = walker.rename_detector

    def changes(self):
        """Get the tree changes for this entry.

        :return: For commits with up to one parent, a list of TreeChange
            objects; if the commit has no parents, these will be relative to the
            empty tree. For merge commits, a list of lists of TreeChange
            objects; see dulwich.diff.tree_changes_for_merge.
        """
        if self._changes is None:
            commit = self.commit
            if not commit.parents:
                changes_func = tree_changes
                parent = None
            elif len(commit.parents) == 1:
                changes_func = tree_changes
                parent = self._store[commit.parents[0]].tree
            else:
                changes_func = tree_changes_for_merge
                parent = [self._store[p].tree for p in commit.parents]
            self._changes = list(changes_func(
              self._store, parent, commit.tree,
              rename_detector=self._rename_detector))
        return self._changes

    def __repr__(self):
        return '<WalkEntry commit=%s, changes=%r>' % (
          self.commit.id, self.changes())


class _CommitTimeQueue(object):
    """Priority queue of WalkEntry objects by commit time."""

    def __init__(self, walker):
        self._walker = walker
        self._store = walker.store
        self._excluded = walker.excluded
        self._pq = []
        self._pq_set = set()
        self._seen = set()
        self._done = set()
        self._min_time = walker.since
        self._last = None
        self._extra_commits_left = _MAX_EXTRA_COMMITS
        self._is_finished = False

        for commit_id in itertools.chain(walker.include, walker.excluded):
            self._push(commit_id)

    def _push(self, commit_id):
        try:
            commit = self._store[commit_id]
        except KeyError:
            raise MissingCommitError(commit_id)
        if commit_id not in self._pq_set and commit_id not in self._done:
            heapq.heappush(self._pq, (-commit.commit_time, commit))
            self._pq_set.add(commit_id)
            self._seen.add(commit_id)

    def _exclude_parents(self, commit):
        excluded = self._excluded
        seen = self._seen
        todo = [commit]
        while todo:
            commit = todo.pop()
            for parent in commit.parents:
                if parent not in excluded and parent in seen:
                    # TODO: This is inefficient unless the object store does
                    # some caching (which DiskObjectStore currently does not).
                    # We could either add caching in this class or pass around
                    # parsed queue entry objects instead of commits.
                    todo.append(self._store[parent])
                excluded.add(parent)

    def next(self):
        if self._is_finished:
            return None
        while self._pq:
            _, commit = heapq.heappop(self._pq)
            sha = commit.id
            self._pq_set.remove(sha)
            if sha in self._done:
                continue
            self._done.add(commit.id)

            for parent_id in commit.parents:
                self._push(parent_id)

            reset_extra_commits = True
            is_excluded = sha in self._excluded
            if is_excluded:
                self._exclude_parents(commit)
                if self._pq and all(c.id in self._excluded
                                    for _, c in self._pq):
                    _, n = self._pq[0]
                    if self._last and n.commit_time >= self._last.commit_time:
                        # If the next commit is newer than the last one, we need
                        # to keep walking in case its parents (which we may not
                        # have seen yet) are excluded. This gives the excluded
                        # set a chance to "catch up" while the commit is still
                        # in the Walker's output queue.
                        reset_extra_commits = True
                    else:
                        reset_extra_commits = False

            if (self._min_time is not None and
                commit.commit_time < self._min_time):
                # We want to stop walking at min_time, but commits at the
                # boundary may be out of order with respect to their parents. So
                # we walk _MAX_EXTRA_COMMITS more commits once we hit this
                # boundary.
                reset_extra_commits = False

            if reset_extra_commits:
                # We're not at a boundary, so reset the counter.
                self._extra_commits_left = _MAX_EXTRA_COMMITS
            else:
                self._extra_commits_left -= 1
                if not self._extra_commits_left:
                    break

            if not is_excluded:
                self._last = commit
                return WalkEntry(self._walker, commit)
        self._is_finished = True
        return None


class Walker(object):
    """Object for performing a walk of commits in a store.

    Walker objects are initialized with a store and other options and can then
    be treated as iterators of Commit objects.
    """

    def __init__(self, store, include, exclude=None, order=ORDER_DATE,
                 reverse=False, max_entries=None, paths=None,
                 rename_detector=None, follow=False, since=None, until=None,
                 queue_cls=_CommitTimeQueue):
        """Constructor.

        :param store: ObjectStore instance for looking up objects.
        :param include: Iterable of SHAs of commits to include along with their
            ancestors.
        :param exclude: Iterable of SHAs of commits to exclude along with their
            ancestors, overriding includes.
        :param order: ORDER_* constant specifying the order of results. Anything
            other than ORDER_DATE may result in O(n) memory usage.
        :param reverse: If True, reverse the order of output, requiring O(n)
            memory.
        :param max_entries: The maximum number of entries to yield, or None for
            no limit.
        :param paths: Iterable of file or subtree paths to show entries for.
        :param rename_detector: diff.RenameDetector object for detecting
            renames.
        :param follow: If True, follow path across renames/copies. Forces a
            default rename_detector.
        :param since: Timestamp to list commits after.
        :param until: Timestamp to list commits before.
        :param queue_cls: A class to use for a queue of commits, supporting the
            iterator protocol. The constructor takes a single argument, the
            Walker.
        """
        # Note: when adding arguments to this method, please also update
        # dulwich.repo.BaseRepo.get_walker
        if order not in ALL_ORDERS:
            raise ValueError('Unknown walk order %s' % order)
        self.store = store
        self.include = include
        self.excluded = set(exclude or [])
        self.order = order
        self.reverse = reverse
        self.max_entries = max_entries
        self.paths = paths and set(paths) or None
        if follow and not rename_detector:
            rename_detector = RenameDetector(store)
        self.rename_detector = rename_detector
        self.follow = follow
        self.since = since
        self.until = until

        self._num_entries = 0
        self._queue = queue_cls(self)
        self._out_queue = collections.deque()

    def _path_matches(self, changed_path):
        if changed_path is None:
            return False
        for followed_path in self.paths:
            if changed_path == followed_path:
                return True
            if (changed_path.startswith(followed_path) and
                changed_path[len(followed_path)] == '/'):
                return True
        return False

    def _change_matches(self, change):
        if not change:
            return False

        old_path = change.old.path
        new_path = change.new.path
        if self._path_matches(new_path):
            if self.follow and change.type in RENAME_CHANGE_TYPES:
                self.paths.add(old_path)
                self.paths.remove(new_path)
            return True
        elif self._path_matches(old_path):
            return True
        return False

    def _should_return(self, entry):
        """Determine if a walk entry should be returned..

        :param entry: The WalkEntry to consider.
        :return: True if the WalkEntry should be returned by this walk, or False
            otherwise (e.g. if it doesn't match any requested paths).
        """
        commit = entry.commit
        if self.since is not None and commit.commit_time < self.since:
            return False
        if self.until is not None and commit.commit_time > self.until:
            return False
        if commit.id in self.excluded:
            return False

        if self.paths is None:
            return True

        if len(commit.parents) > 1:
            for path_changes in entry.changes():
                # For merge commits, only include changes with conflicts for
                # this path. Since a rename conflict may include different
                # old.paths, we have to check all of them.
                for change in path_changes:
                    if self._change_matches(change):
                        return True
        else:
            for change in entry.changes():
                if self._change_matches(change):
                    return True
        return None

    def _next(self):
        max_entries = self.max_entries
        while max_entries is None or self._num_entries < max_entries:
            entry = self._queue.next()
            if entry is not None:
                self._out_queue.append(entry)
            if entry is None or len(self._out_queue) > _MAX_EXTRA_COMMITS:
                if not self._out_queue:
                    return None
                entry = self._out_queue.popleft()
                if self._should_return(entry):
                    self._num_entries += 1
                    return entry
        return None

    def _reorder(self, results):
        """Possibly reorder a results iterator.

        :param results: An iterator of WalkEntry objects, in the order returned
            from the queue_cls.
        :return: An iterator or list of WalkEntry objects, in the order required
            by the Walker.
        """
        if self.order == ORDER_TOPO:
            results = _topo_reorder(results)
        if self.reverse:
            results = reversed(list(results))
        return results

    def __iter__(self):
        return iter(self._reorder(iter(self._next, None)))


def _topo_reorder(entries):
    """Reorder an iterable of entries topologically.

    This works best assuming the entries are already in almost-topological
    order, e.g. in commit time order.

    :param entries: An iterable of WalkEntry objects.
    :return: iterator over WalkEntry objects from entries in FIFO order, except
        where a parent would be yielded before any of its children.
    """
    todo = collections.deque()
    pending = {}
    num_children = defaultdict(int)
    for entry in entries:
        todo.append(entry)
        for p in entry.commit.parents:
            num_children[p] += 1

    while todo:
        entry = todo.popleft()
        commit = entry.commit
        commit_id = commit.id
        if num_children[commit_id]:
            pending[commit_id] = entry
            continue
        for parent_id in commit.parents:
            num_children[parent_id] -= 1
            if not num_children[parent_id]:
                parent_entry = pending.pop(parent_id, None)
                if parent_entry:
                    todo.appendleft(parent_entry)
        yield entry

########NEW FILE########
__FILENAME__ = web
# web.py -- WSGI smart-http server
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""HTTP server for dulwich that implements the git smart HTTP protocol."""

from cStringIO import StringIO
import gzip
import os
import re
import sys
import time

try:
    from urlparse import parse_qs
except ImportError:
    from dulwich._compat import parse_qs
from dulwich import log_utils
from dulwich.protocol import (
    ReceivableProtocol,
    )
from dulwich.repo import (
    Repo,
    )
from dulwich.server import (
    DictBackend,
    DEFAULT_HANDLERS,
    generate_info_refs,
    generate_objects_info_packs,
    )


logger = log_utils.getLogger(__name__)


# HTTP error strings
HTTP_OK = '200 OK'
HTTP_NOT_FOUND = '404 Not Found'
HTTP_FORBIDDEN = '403 Forbidden'
HTTP_ERROR = '500 Internal Server Error'


def date_time_string(timestamp=None):
    # From BaseHTTPRequestHandler.date_time_string in BaseHTTPServer.py in the
    # Python 2.6.5 standard library, following modifications:
    #  - Made a global rather than an instance method.
    #  - weekdayname and monthname are renamed and locals rather than class
    #    variables.
    # Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = [None,
              'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    if timestamp is None:
        timestamp = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    return '%s, %02d %3s %4d %02d:%02d:%02d GMD' % (
            weekdays[wd], day, months[month], year, hh, mm, ss)


def url_prefix(mat):
    """Extract the URL prefix from a regex match.

    :param mat: A regex match object.
    :returns: The URL prefix, defined as the text before the match in the
        original string. Normalized to start with one leading slash and end with
        zero.
    """
    return '/' + mat.string[:mat.start()].strip('/')


def get_repo(backend, mat):
    """Get a Repo instance for the given backend and URL regex match."""
    return backend.open_repository(url_prefix(mat))


def send_file(req, f, content_type):
    """Send a file-like object to the request output.

    :param req: The HTTPGitRequest object to send output to.
    :param f: An open file-like object to send; will be closed.
    :param content_type: The MIME type for the file.
    :return: Iterator over the contents of the file, as chunks.
    """
    if f is None:
        yield req.not_found('File not found')
        return
    try:
        req.respond(HTTP_OK, content_type)
        while True:
            data = f.read(10240)
            if not data:
                break
            yield data
        f.close()
    except IOError:
        f.close()
        yield req.error('Error reading file')
    except:
        f.close()
        raise


def _url_to_path(url):
    return url.replace('/', os.path.sep)


def get_text_file(req, backend, mat):
    req.nocache()
    path = _url_to_path(mat.group())
    logger.info('Sending plain text file %s', path)
    return send_file(req, get_repo(backend, mat).get_named_file(path),
                     'text/plain')


def get_loose_object(req, backend, mat):
    sha = mat.group(1) + mat.group(2)
    logger.info('Sending loose object %s', sha)
    object_store = get_repo(backend, mat).object_store
    if not object_store.contains_loose(sha):
        yield req.not_found('Object not found')
        return
    try:
        data = object_store[sha].as_legacy_object()
    except IOError:
        yield req.error('Error reading object')
        return
    req.cache_forever()
    req.respond(HTTP_OK, 'application/x-git-loose-object')
    yield data


def get_pack_file(req, backend, mat):
    req.cache_forever()
    path = _url_to_path(mat.group())
    logger.info('Sending pack file %s', path)
    return send_file(req, get_repo(backend, mat).get_named_file(path),
                     'application/x-git-packed-objects')


def get_idx_file(req, backend, mat):
    req.cache_forever()
    path = _url_to_path(mat.group())
    logger.info('Sending pack file %s', path)
    return send_file(req, get_repo(backend, mat).get_named_file(path),
                     'application/x-git-packed-objects-toc')


def get_info_refs(req, backend, mat):
    params = parse_qs(req.environ['QUERY_STRING'])
    service = params.get('service', [None])[0]
    if service and not req.dumb:
        handler_cls = req.handlers.get(service, None)
        if handler_cls is None:
            yield req.forbidden('Unsupported service %s' % service)
            return
        req.nocache()
        write = req.respond(HTTP_OK, 'application/x-%s-advertisement' % service)
        proto = ReceivableProtocol(StringIO().read, write)
        handler = handler_cls(backend, [url_prefix(mat)], proto,
                              http_req=req, advertise_refs=True)
        handler.proto.write_pkt_line('# service=%s\n' % service)
        handler.proto.write_pkt_line(None)
        handler.handle()
    else:
        # non-smart fallback
        # TODO: select_getanyfile() (see http-backend.c)
        req.nocache()
        req.respond(HTTP_OK, 'text/plain')
        logger.info('Emulating dumb info/refs')
        repo = get_repo(backend, mat)
        for text in generate_info_refs(repo):
            yield text


def get_info_packs(req, backend, mat):
    req.nocache()
    req.respond(HTTP_OK, 'text/plain')
    logger.info('Emulating dumb info/packs')
    return generate_objects_info_packs(get_repo(backend, mat))


class _LengthLimitedFile(object):
    """Wrapper class to limit the length of reads from a file-like object.

    This is used to ensure EOF is read from the wsgi.input object once
    Content-Length bytes are read. This behavior is required by the WSGI spec
    but not implemented in wsgiref as of 2.5.
    """

    def __init__(self, input, max_bytes):
        self._input = input
        self._bytes_avail = max_bytes

    def read(self, size=-1):
        if self._bytes_avail <= 0:
            return ''
        if size == -1 or size > self._bytes_avail:
            size = self._bytes_avail
        self._bytes_avail -= size
        return self._input.read(size)

    # TODO: support more methods as necessary


def handle_service_request(req, backend, mat):
    service = mat.group().lstrip('/')
    logger.info('Handling service request for %s', service)
    handler_cls = req.handlers.get(service, None)
    if handler_cls is None:
        yield req.forbidden('Unsupported service %s' % service)
        return
    req.nocache()
    write = req.respond(HTTP_OK, 'application/x-%s-result' % service)
    proto = ReceivableProtocol(req.environ['wsgi.input'].read, write)
    handler = handler_cls(backend, [url_prefix(mat)], proto, http_req=req)
    handler.handle()


class HTTPGitRequest(object):
    """Class encapsulating the state of a single git HTTP request.

    :ivar environ: the WSGI environment for the request.
    """

    def __init__(self, environ, start_response, dumb=False, handlers=None):
        self.environ = environ
        self.dumb = dumb
        self.handlers = handlers
        self._start_response = start_response
        self._cache_headers = []
        self._headers = []

    def add_header(self, name, value):
        """Add a header to the response."""
        self._headers.append((name, value))

    def respond(self, status=HTTP_OK, content_type=None, headers=None):
        """Begin a response with the given status and other headers."""
        if headers:
            self._headers.extend(headers)
        if content_type:
            self._headers.append(('Content-Type', content_type))
        self._headers.extend(self._cache_headers)

        return self._start_response(status, self._headers)

    def not_found(self, message):
        """Begin a HTTP 404 response and return the text of a message."""
        self._cache_headers = []
        logger.info('Not found: %s', message)
        self.respond(HTTP_NOT_FOUND, 'text/plain')
        return message

    def forbidden(self, message):
        """Begin a HTTP 403 response and return the text of a message."""
        self._cache_headers = []
        logger.info('Forbidden: %s', message)
        self.respond(HTTP_FORBIDDEN, 'text/plain')
        return message

    def error(self, message):
        """Begin a HTTP 500 response and return the text of a message."""
        self._cache_headers = []
        logger.error('Error: %s', message)
        self.respond(HTTP_ERROR, 'text/plain')
        return message

    def nocache(self):
        """Set the response to never be cached by the client."""
        self._cache_headers = [
          ('Expires', 'Fri, 01 Jan 1980 00:00:00 GMT'),
          ('Pragma', 'no-cache'),
          ('Cache-Control', 'no-cache, max-age=0, must-revalidate'),
          ]

    def cache_forever(self):
        """Set the response to be cached forever by the client."""
        now = time.time()
        self._cache_headers = [
          ('Date', date_time_string(now)),
          ('Expires', date_time_string(now + 31536000)),
          ('Cache-Control', 'public, max-age=31536000'),
          ]


class HTTPGitApplication(object):
    """Class encapsulating the state of a git WSGI application.

    :ivar backend: the Backend object backing this application
    """

    services = {
      ('GET', re.compile('/HEAD$')): get_text_file,
      ('GET', re.compile('/info/refs$')): get_info_refs,
      ('GET', re.compile('/objects/info/alternates$')): get_text_file,
      ('GET', re.compile('/objects/info/http-alternates$')): get_text_file,
      ('GET', re.compile('/objects/info/packs$')): get_info_packs,
      ('GET', re.compile('/objects/([0-9a-f]{2})/([0-9a-f]{38})$')): get_loose_object,
      ('GET', re.compile('/objects/pack/pack-([0-9a-f]{40})\\.pack$')): get_pack_file,
      ('GET', re.compile('/objects/pack/pack-([0-9a-f]{40})\\.idx$')): get_idx_file,

      ('POST', re.compile('/git-upload-pack$')): handle_service_request,
      ('POST', re.compile('/git-receive-pack$')): handle_service_request,
    }

    def __init__(self, backend, dumb=False, handlers=None, fallback_app=None):
        self.backend = backend
        self.dumb = dumb
        self.handlers = dict(DEFAULT_HANDLERS)
        self.fallback_app = fallback_app
        if handlers is not None:
            self.handlers.update(handlers)

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        method = environ['REQUEST_METHOD']
        req = HTTPGitRequest(environ, start_response, dumb=self.dumb,
                             handlers=self.handlers)
        # environ['QUERY_STRING'] has qs args
        handler = None
        for smethod, spath in self.services.iterkeys():
            if smethod != method:
                continue
            mat = spath.search(path)
            if mat:
                handler = self.services[smethod, spath]
                break

        if handler is None:
            if self.fallback_app is not None:
                return self.fallback_app(environ, start_response)
            else:
                return req.not_found('Sorry, that method is not supported')

        return handler(req, self.backend, mat)


class GunzipFilter(object):
    """WSGI middleware that unzips gzip-encoded requests before
    passing on to the underlying application.
    """

    def __init__(self, application):
        self.app = application

    def __call__(self, environ, start_response):
        if environ.get('HTTP_CONTENT_ENCODING', '') == 'gzip':
            environ.pop('HTTP_CONTENT_ENCODING')
            if 'CONTENT_LENGTH' in environ:
                del environ['CONTENT_LENGTH']
            environ['wsgi.input'] = gzip.GzipFile(filename=None,
                fileobj=environ['wsgi.input'], mode='r')
        return self.app(environ, start_response)


class LimitedInputFilter(object):
    """WSGI middleware that limits the input length of a request to that
    specified in Content-Length.
    """

    def __init__(self, application):
        self.app = application

    def __call__(self, environ, start_response):
        # This is not necessary if this app is run from a conforming WSGI
        # server. Unfortunately, there's no way to tell that at this point.
        # TODO: git may used HTTP/1.1 chunked encoding instead of specifying
        # content-length
        content_length = environ.get('CONTENT_LENGTH', '')
        if content_length:
            environ['wsgi.input'] = _LengthLimitedFile(
                environ['wsgi.input'], int(content_length))
        return self.app(environ, start_response)


def make_wsgi_chain(*args, **kwargs):
    """Factory function to create an instance of HTTPGitApplication,
    correctly wrapped with needed middleware.
    """
    app = HTTPGitApplication(*args, **kwargs)
    wrapped_app = GunzipFilter(LimitedInputFilter(app))
    return wrapped_app


# The reference server implementation is based on wsgiref, which is not
# distributed with python 2.4. If wsgiref is not present, users will not be
# able to use the HTTP server without a little extra work.
try:
    from wsgiref.simple_server import (
        WSGIRequestHandler,
        ServerHandler,
        WSGIServer,
        make_server,
    )
    class ServerHandlerLogger(ServerHandler):
        """ServerHandler that uses dulwich's logger for logging exceptions."""

        def log_exception(self, exc_info):
            logger.exception('Exception happened during processing of request',
                             exc_info=exc_info)

        def log_message(self, format, *args):
            logger.info(format, *args)

        def log_error(self, *args):
            logger.error(*args)

    class WSGIRequestHandlerLogger(WSGIRequestHandler):
        """WSGIRequestHandler that uses dulwich's logger for logging exceptions."""

        def log_exception(self, exc_info):
            logger.exception('Exception happened during processing of request',
                             exc_info=exc_info)

        def log_message(self, format, *args):
            logger.info(format, *args)

        def log_error(self, *args):
            logger.error(*args)

        def handle(self):
            """Handle a single HTTP request"""

            self.raw_requestline = self.rfile.readline()
            if not self.parse_request(): # An error code has been sent, just exit
                return

            handler = ServerHandlerLogger(
                self.rfile, self.wfile, self.get_stderr(), self.get_environ()
            )
            handler.request_handler = self      # backpointer for logging
            handler.run(self.server.get_app())

    class WSGIServerLogger(WSGIServer):
        def handle_error(self, request, client_address):
            """Handle an error. """
            logger.exception('Exception happened during processing of request from %s' % str(client_address))

    def main(argv=sys.argv):
        """Entry point for starting an HTTP git server."""
        if len(argv) > 1:
            gitdir = argv[1]
        else:
            gitdir = os.getcwd()

        # TODO: allow serving on other addresses/ports via command-line flag
        listen_addr = ''
        port = 8000

        log_utils.default_logging_config()
        backend = DictBackend({'/': Repo(gitdir)})
        app = make_wsgi_chain(backend)
        server = make_server(listen_addr, port, app,
                             handler_class=WSGIRequestHandlerLogger,
                             server_class=WSGIServerLogger)
        logger.info('Listening for HTTP connections on %s:%d', listen_addr,
                    port)
        server.serve_forever()

except ImportError:
    # No wsgiref found; don't provide the reference functionality, but leave
    # the rest of the WSGI-based implementation.
    def main(argv=sys.argv):
        """Stub entry point for failing to start a server without wsgiref."""
        sys.stderr.write(
            'Sorry, the wsgiref module is required for dul-web.\n')
        sys.exit(1)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = _compat
# _compat.py -- For dealing with python2.4 oddness
# Copyright (C) 2008 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Misc utilities to work with python <2.6.

These utilities can all be deleted when dulwich decides it wants to stop
support for python <2.6.
"""
try:
    import hashlib
except ImportError:
    import sha

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

try:
    from os import SEEK_CUR, SEEK_END
except ImportError:
    SEEK_CUR = 1
    SEEK_END = 2

import struct


class defaultdict(dict):
    """A python 2.4 equivalent of collections.defaultdict."""

    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
            not hasattr(default_factory, '__call__')):
            raise TypeError('first argument must be callable')
        dict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))
    def __repr__(self):
        return 'defaultdict(%s, %s)' % (self.default_factory,
                                        dict.__repr__(self))


def make_sha(source=''):
    """A python2.4 workaround for the sha/hashlib module fiasco."""
    try:
        return hashlib.sha1(source)
    except NameError:
        sha1 = sha.sha(source)
        return sha1


def unpack_from(fmt, buf, offset=0):
    """A python2.4 workaround for struct missing unpack_from."""
    try:
        return struct.unpack_from(fmt, buf, offset)
    except AttributeError:
        b = buf[offset:offset+struct.calcsize(fmt)]
        return struct.unpack(fmt, b)


try:
    from itertools import permutations
except ImportError:
    # Implementation of permutations from Python 2.6 documentation:
    # http://docs.python.org/2.6/library/itertools.html#itertools.permutations
    # Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved
    # Modified syntax slightly to run under Python 2.4.
    def permutations(iterable, r=None):
        # permutations('ABCD', 2) --> AB AC AD BA BC BD CA CB CD DA DB DC
        # permutations(range(3)) --> 012 021 102 120 201 210
        pool = tuple(iterable)
        n = len(pool)
        if r is None:
            r = n
        if r > n:
            return
        indices = range(n)
        cycles = range(n, n-r, -1)
        yield tuple(pool[i] for i in indices[:r])
        while n:
            for i in reversed(range(r)):
                cycles[i] -= 1
                if cycles[i] == 0:
                    indices[i:] = indices[i+1:] + indices[i:i+1]
                    cycles[i] = n - i
                else:
                    j = cycles[i]
                    indices[i], indices[-j] = indices[-j], indices[i]
                    yield tuple(pool[i] for i in indices[:r])
                    break
            else:
                return


try:
    all = all
except NameError:
    # Implementation of permutations from Python 2.6 documentation:
    # http://docs.python.org/2.6/library/functions.html#all
    # Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved
    # Licensed under the Python Software Foundation License.
    def all(iterable):
        for element in iterable:
            if not element:
                return False
        return True


try:
    from collections import namedtuple
except ImportError:
    # Recipe for namedtuple from http://code.activestate.com/recipes/500261/
    # Copyright (c) 2007 Python Software Foundation; All Rights Reserved
    # Licensed under the Python Software Foundation License.
    from operator import itemgetter as _itemgetter
    from keyword import iskeyword as _iskeyword
    import sys as _sys

    def namedtuple(typename, field_names, verbose=False, rename=False):
        """Returns a new subclass of tuple with named fields.

        >>> Point = namedtuple('Point', 'x y')
        >>> Point.__doc__                   # docstring for the new class
        'Point(x, y)'
        >>> p = Point(11, y=22)             # instantiate with positional args or keywords
        >>> p[0] + p[1]                     # indexable like a plain tuple
        33
        >>> x, y = p                        # unpack like a regular tuple
        >>> x, y
        (11, 22)
        >>> p.x + p.y                       # fields also accessable by name
        33
        >>> d = p._asdict()                 # convert to a dictionary
        >>> d['x']
        11
        >>> Point(**d)                      # convert from a dictionary
        Point(x=11, y=22)
        >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
        Point(x=100, y=22)

        """

        # Parse and validate the field names.  Validation serves two purposes,
        # generating informative error messages and preventing template injection attacks.
        if isinstance(field_names, basestring):
            field_names = field_names.replace(',', ' ').split() # names separated by whitespace and/or commas
        field_names = tuple(map(str, field_names))
        if rename:
            names = list(field_names)
            seen = set()
            for i, name in enumerate(names):
                if (not min(c.isalnum() or c=='_' for c in name) or _iskeyword(name)
                    or not name or name[0].isdigit() or name.startswith('_')
                    or name in seen):
                        names[i] = '_%d' % i
                seen.add(name)
            field_names = tuple(names)
        for name in (typename,) + field_names:
            if not min(c.isalnum() or c=='_' for c in name):
                raise ValueError('Type names and field names can only contain alphanumeric characters and underscores: %r' % name)
            if _iskeyword(name):
                raise ValueError('Type names and field names cannot be a keyword: %r' % name)
            if name[0].isdigit():
                raise ValueError('Type names and field names cannot start with a number: %r' % name)
        seen_names = set()
        for name in field_names:
            if name.startswith('_') and not rename:
                raise ValueError('Field names cannot start with an underscore: %r' % name)
            if name in seen_names:
                raise ValueError('Encountered duplicate field name: %r' % name)
            seen_names.add(name)

        # Create and fill-in the class template
        numfields = len(field_names)
        argtxt = repr(field_names).replace("'", "")[1:-1]   # tuple repr without parens or quotes
        reprtxt = ', '.join('%s=%%r' % name for name in field_names)
        template = '''class %(typename)s(tuple):
        '%(typename)s(%(argtxt)s)' \n
        __slots__ = () \n
        _fields = %(field_names)r \n
        def __new__(_cls, %(argtxt)s):
            return _tuple.__new__(_cls, (%(argtxt)s)) \n
        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new %(typename)s object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != %(numfields)d:
                raise TypeError('Expected %(numfields)d arguments, got %%d' %% len(result))
            return result \n
        def __repr__(self):
            return '%(typename)s(%(reprtxt)s)' %% self \n
        def _asdict(self):
            'Return a new dict which maps field names to their values'
            return dict(zip(self._fields, self)) \n
        def _replace(_self, **kwds):
            'Return a new %(typename)s object replacing specified fields with new values'
            result = _self._make(map(kwds.pop, %(field_names)r, _self))
            if kwds:
                raise ValueError('Got unexpected field names: %%r' %% kwds.keys())
            return result \n
        def __getnewargs__(self):
            return tuple(self) \n\n''' % locals()
        for i, name in enumerate(field_names):
            template += '        %s = _property(_itemgetter(%d))\n' % (name, i)
        if verbose:
            print template

        # Execute the template string in a temporary namespace
        namespace = dict(_itemgetter=_itemgetter, __name__='namedtuple_%s' % typename,
                         _property=property, _tuple=tuple)
        try:
            exec template in namespace
        except SyntaxError, e:
            raise SyntaxError(e.message + ':\n' + template)
        result = namespace[typename]

        # For pickling to work, the __module__ variable needs to be set to the frame
        # where the named tuple is created.  Bypass this step in enviroments where
        # sys._getframe is not defined (Jython for example) or sys._getframe is not
        # defined for arguments greater than 0 (IronPython).
        try:
            result.__module__ = _sys._getframe(1).f_globals.get('__name__', '__main__')
        except (AttributeError, ValueError):
            pass

        return result


# Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
# Passes Python2.7's test suite and incorporates all the latest updates.
# Copyright (C) Raymond Hettinger, MIT license

try:
    from thread import get_ident as _get_ident
except ImportError:
    from dummy_thread import get_ident as _get_ident

try:
    from _abcoll import KeysView, ValuesView, ItemsView
except ImportError:
    pass

class OrderedDict(dict):
    'Dictionary that remembers insertion order'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(self, *args, **kwds):
        '''Initialize an ordered dictionary.  Signature is the same as for
        regular dictionaries, but keyword arguments are not recommended
        because their insertion order is arbitrary.

        '''
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []                     # sentinel node
            root[:] = [root, root, None]
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link which goes at the end of the linked
        # list, and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which is
        # then removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, key = self.__map.pop(key)
        link_prev[1] = link_next
        link_next[0] = link_prev

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        root = self.__root
        curr = root[0]
        while curr is not root:
            yield curr[2]
            curr = curr[0]

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        try:
            for node in self.__map.itervalues():
                del node[:]
            root = self.__root
            root[:] = [root, root, None]
            self.__map.clear()
        except AttributeError:
            pass
        dict.clear(self)

    def popitem(self, last=True):
        """od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        """
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root[0]
            link_prev = link[0]
            link_prev[1] = root
            root[0] = link_prev
        else:
            link = root[1]
            link_next = link[1]
            root[1] = link_next
            link_next[0] = root
        key = link[2]
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        """'od.keys() -> list of keys in od"""
        return list(self)

    def values(self):
        """od.values() -> list of values in od"""
        return [self[key] for key in self]

    def items(self):
        """od.items() -> list of (key, value) pairs in od"""
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        """od.iterkeys() -> an iterator over the keys in od"""
        return iter(self)

    def itervalues(self):
        """od.itervalues -> an iterator over the values in od"""
        for k in self:
            yield self[k]

    def iteritems(self):
        """od.iteritems -> an iterator over the (key, value) items in od"""
        for k in self:
            yield (k, self[k])

    def update(*args, **kwds):
        """od.update(E, **F) -> None.  Update od from dict/iterable E and F.

        If E is a dict instance, does:           for k in E: od[k] = E[k]
        If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
        Or if E is an iterable of items, does:   for k, v in E: od[k] = v
        In either case, this is followed by:     for k, v in F.items(): od[k] = v

        """
        if len(args) > 2:
            raise TypeError('update() takes at most 2 positional '
                            'arguments (%d given)' % (len(args),))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        # Make progressively weaker assumptions about "other"
        other = ()
        if len(args) == 2:
            other = args[1]
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, 'keys'):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    __update = update  # let subclasses override update without breaking __init__

    __marker = object()

    def pop(self, key, default=__marker):
        """od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.

        """
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        call_key = id(self), _get_ident()
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())
        finally:
            del _repr_running[call_key]

    def __reduce__(self):
        'Return state information for pickling'
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None).

        '''
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # -- the following methods are only used in Python 2.7 --

    def viewkeys(self):
        "od.viewkeys() -> a set-like object providing a view on od's keys"
        return KeysView(self)

    def viewvalues(self):
        "od.viewvalues() -> an object providing a view on od's values"
        return ValuesView(self)

    def viewitems(self):
        "od.viewitems() -> a set-like object providing a view on od's items"
        return ItemsView(self)

########NEW FILE########
