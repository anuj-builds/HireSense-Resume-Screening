
import { useCallback, useEffect, useState } from "react";
import {
  LayoutDashboard, FileText, Users, BriefcaseBusiness, Settings,
  Bell, Search, Upload, ArrowUpRight, CheckCircle2, Clock3,
  UserCheck, MoreHorizontal, Sparkles, RefreshCw
} from "lucide-react";
import {
  getRankedCandidates,
  getResumes,
  updateShortlist,
  uploadResume,
} from "./api";
import "./App.css";

const JOB_ID = 1;

function formatName(filename = "") {
  return filename
    .replace(/\.[^/.]+$/, "")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function initials(name = "") {
  return name.split(/\s+/).filter(Boolean).slice(0, 2)
    .map((part) => part[0]).join("").toUpperCase() || "CA";
}

function App() {
  const [active, setActive] = useState("Overview");
  const [search, setSearch] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [totalResumes, setTotalResumes] = useState(0);
  const [jobTitle, setJobTitle] = useState("Python Developer Intern");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [notice, setNotice] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [ranking, resumeData] = await Promise.all([
        getRankedCandidates(JOB_ID),
        getResumes(),
      ]);

      setJobTitle(ranking.job_title || "Candidate Screening");
      setCandidates((ranking.candidates || []).map((candidate) => {
        const name = formatName(candidate.original_filename);
        return {
          ...candidate,
          name,
          initials: initials(name),
          role: ranking.job_title || "Candidate",
          score: Number(candidate.overall_score) || 0,
          skills: candidate.matched_skills || [],
          status: candidate.shortlist_status || "under_review",
        };
      }));
      setTotalResumes(resumeData.total ?? (resumeData.resumes || []).length);
    } catch (err) {
      setError(err.message || "Could not load data from the backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleShortlist(candidate) {
    if (candidate.status === "shortlisted") return;

    setBusyId(candidate.resume_id);
    setNotice("");
    try {
      await updateShortlist(JOB_ID, candidate.resume_id, "shortlisted");
      setNotice(`${candidate.name} was shortlisted successfully.`);
      await loadData();
    } catch (err) {
      setError(`Could not shortlist candidate: ${err.message}`);
    } finally {
      setBusyId(null);
    }
  }

  
async function handleUpload(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;

  setNotice("");
  setError("");

  for (const file of files) {
    try {
      setNotice(`Uploading ${file.name}...`);
      await uploadResume(file);
      setNotice(`${file.name} uploaded successfully!`);
    } catch (err) {
       setError(`${file.name}: ${err.message}`);
       setNotice("");
}
  }

  event.target.value = "";
  await loadData();
}


  const filtered = candidates.filter((candidate) =>
    `${candidate.name} ${candidate.role} ${(candidate.skills || []).join(" ")}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  const shortlisted = candidates.filter(
    (candidate) => candidate.status === "shortlisted"
  ).length;

  const underReview = candidates.filter(
    (candidate) => candidate.status !== "shortlisted"
  ).length;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><Sparkles size={23} /></div>
          <div><strong>HireSense</strong><span>AI RECRUITMENT</span></div>
        </div>

        <p className="nav-label">WORKSPACE</p>
        {[
          { label: "Overview", icon: LayoutDashboard },
          { label: "Candidates", icon: Users },
          { label: "Resumes", icon: FileText },
          { label: "Job Positions", icon: BriefcaseBusiness },
        ].map(({ label, icon: Icon }) => (
          <button key={label}
            className={`nav-item ${active === label ? "active" : ""}`}
            onClick={() => setActive(label)}>
            <Icon size={19} /><span>{label}</span>
          </button>
        ))}

        <div className="sidebar-bottom">
          <button className={`nav-item ${active === "Settings" ? "active" : ""}`}
            onClick={() => setActive("Settings")}>
            <Settings size={19} /><span>Settings</span>
          </button>
          <div className="profile">
            <div className="avatar profile-avatar">AS</div>
            <div className="profile-text"><strong>Admin User</strong><span>Recruiter</span></div>
            <MoreHorizontal size={20} />
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs">Workspace <span>/</span> <strong>{active}</strong></div>
          <div className="top-actions">
            <span className="status-dot"></span>
            <span className="system-status">Backend connected</span>
            <button className="icon-button" aria-label="Refresh data" onClick={loadData}>
              <RefreshCw size={17} />
            </button>
            <button className="icon-button" aria-label="Notifications"><Bell size={19} /></button>
            <div className="avatar top-avatar">AS</div>
          </div>
        </header>

        <section className="page-content">
          <div className="welcome-row">
            <div>
              <div className="eyebrow"><Sparkles size={14} /> LIVE SCREENING DATA</div>
              <h1>{active === "Overview" ? "Recruitment overview" : active}</h1>
              <p className="subtitle">
                {jobTitle} · Candidate matches from your screening API.
              </p>
            </div>
            <button className="primary-button"
              onClick={() => document.getElementById("resume-upload")?.click()}>
              <Upload size={17} /> Upload resumes
            </button>
            <input id="resume-upload" type="file" accept=".pdf,.doc,.docx" multiple hidden
              onChange={handleUpload} />
          </div>

          {error && <div className="error-message">{error}</div>}
          {notice && <div className="success-message">{notice}</div>}

          <div className="stats-grid">
            <StatCard icon={FileText} label="Total resumes" value={totalResumes} change="Live" note="Uploaded to backend" color="blue" />
            <StatCard icon={UserCheck} label="Shortlisted" value={shortlisted} change="Live" note="From screening API" color="green" />
            <StatCard icon={Clock3} label="Under review" value={underReview} change="Live" note="Candidates not shortlisted" color="orange" />
            <StatCard icon={BriefcaseBusiness} label="Candidates ranked" value={candidates.length} change="Live" note="For the selected job" color="purple" />
          </div>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Candidate screening</h2>
                <p>Real ranking scores and skills returned by your backend.</p>
              </div>
              <button className="secondary-button" onClick={loadData}>
                Refresh results <RefreshCw size={15} />
              </button>
            </div>

            <div className="table-toolbar">
              <div className="search-box">
                <Search size={17} />
                <input value={search} onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search resumes or matched skills..." />
              </div>
              <span className="candidate-count">{filtered.length} candidates</span>
            </div>

            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>CANDIDATE / RESUME</th>
                    <th>MATCHED SKILLS</th>
                    <th>MATCH SCORE</th>
                    <th>STATUS</th>
                    <th>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan="5" className="empty-state">Loading real screening results…</td></tr>
                  ) : filtered.map((candidate) => (
                    <tr key={candidate.resume_id}>
                      <td>
                        <div className="candidate-cell">
                          <div className="avatar candidate-avatar">{candidate.initials}</div>
                          <div>
                            <strong>{candidate.name}</strong>
                            <span>{candidate.original_filename}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className="skill-list">
                          {candidate.skills.length
                            ? candidate.skills.slice(0, 3).map((skill) =>
                              <span className="skill-chip" key={skill}>{skill}</span>)
                            : <span className="skill-chip">No matched skills</span>}
                        </div>
                      </td>
                      <td>
                        <div className="score-cell">
                          <div className="score-track">
                            <div className="score-fill"
                              style={{ width: `${Math.min(100, Math.max(0, candidate.score))}%` }} />
                          </div>
                          <strong>{candidate.score.toFixed(1)}%</strong>
                        </div>
                      </td>
                      <td>
                        <span className={`status-pill ${candidate.status === "shortlisted" ? "shortlisted" : "review"}`}>
                          <span />
                          {candidate.status.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td>
                        <button
                          className={`action-button ${candidate.status === "shortlisted" ? "selected" : ""}`}
                          disabled={candidate.status === "shortlisted" || busyId === candidate.resume_id}
                          onClick={() => handleShortlist(candidate)}>
                          {candidate.status === "shortlisted"
                            ? <><CheckCircle2 size={15} /> Shortlisted</>
                            : busyId === candidate.resume_id ? "Saving…" : "Shortlist"}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!loading && filtered.length === 0 && (
                    <tr><td colSpan="5" className="empty-state">No candidates found for this search.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="panel-footer">
              <span>{loading ? "Loading…" : `Showing ${filtered.length} of ${candidates.length} ranked candidates`}</span>
              <span className="demo-label"><span /> Live API data</span>
            </div>
          </section>

          <footer className="footer">
            <span>HireSense · AI Resume Screening</span>
            <span>Prototype v1.0</span>
          </footer>
        </section>
      </main>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, change, note, color }) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <div className={`stat-icon ${color}`}><Icon size={20} /></div>
        <span className="stat-change">{change}</span>
      </div>
      <p>{label}</p>
      <h2>{value}</h2>
      <span className="stat-note">{note}</span>
    </div>
  );
}

export default App;
