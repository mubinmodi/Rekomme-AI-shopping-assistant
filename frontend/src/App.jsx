import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowRight,
  BadgeCheck,
  BarChart3,
  BookOpen,
  Check,
  ChevronDown,
  CircleUserRound,
  Clock3,
  ExternalLink,
  Headphones,
  Layers3,
  LogOut,
  Menu,
  MessageCircleMore,
  MessageSquareText,
  Plus,
  Search,
  Send,
  ShoppingBag,
  Sparkles,
  Star,
  Tag,
  TrendingDown,
  TrendingUp,
  UsersRound,
  Video,
  X,
} from "lucide-react";
import { api, authStore } from "./api";

const EXAMPLES = [
  {
    label: "Work from home",
    query: "Best headphones under $200 for working from home",
    icon: Headphones
  },
  {
    label: "Travel essential",
    query: "Best noise cancelling headphones for long flights",
    icon: ShoppingBag
  },
  {
    label: "Audiophile pick",
    query: "Over-ear headphones for audiophiles under $500",
    icon: Star
  },
  {
    label: "Everyday value",
    query: "Wireless earbuds with good bass and long battery life",
    icon: BadgeCheck
  }
];

const FOLLOW_UP_SIGNALS = [
  "which one",
  "what about",
  "tell me more",
  "compare",
  "versus",
  "difference",
  "better",
  "pros",
  "cons",
  "durability",
  "comfort",
  "battery",
  "worth",
  "should i",
  "first one",
  "second one",
  "that one",
  "cheaper",
  "more expensive"
];

function isFollowUpQuery(prompt) {
  const lower = prompt.toLowerCase().trim();
  if (lower.split(/\s+/).length <= 5) return true;
  return FOLLOW_UP_SIGNALS.some((signal) => lower.includes(signal));
}

function Logo({ compact = false }) {
  return (
    <div className={`logo ${compact ? "logo--compact" : ""}`} aria-label="Rekomme">
      <span className="logo__mark">
        <Sparkles size={18} strokeWidth={2.4} />
      </span>
      {!compact && (
        <span className="logo__type">
          rekomme<span>.</span>
        </span>
      )}
    </div>
  );
}

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    username: "",
    password: "",
    email: "",
    full_name: ""
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (mode === "register") {
        if (!form.username || !form.password || !form.email) {
          throw new Error("Username, password, and email are required.");
        }
        await api.register(form);
        setNotice("Your account is ready. Sign in to start shopping smarter.");
        setMode("login");
      } else {
        const tokens = await api.login(form.username, form.password);
        authStore.save(tokens, form.username);
        onAuthenticated();
      }
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const useDemo = () => {
    setMode("login");
    setForm((current) => ({ ...current, username: "reviewer", password: "rekomme" }));
    setError("");
  };

  return (
    <main className="auth-shell">
      <section className="auth-story">
        <div className="auth-story__top">
          <Logo />
          <span className="eyebrow eyebrow--light">Community intelligence for better buys</span>
        </div>

        <div className="auth-story__content">
          <p className="auth-story__kicker">Less scrolling. More knowing.</p>
          <h1>Find the product people still love after the unboxing.</h1>
          <p className="auth-story__lede">
            Rekomme distills real owner experiences, trusted reviews, and live market signals
            into one clear recommendation.
          </p>

          <div className="signal-card">
            <div className="signal-card__header">
              <span>Community signal</span>
              <span className="signal-card__live"><i /> Live</span>
            </div>
            <div className="signal-card__meter">
              <span style={{ width: "86%" }} />
            </div>
            <div className="signal-card__footer">
              <strong>86% owner confidence</strong>
              <span>across 1,240+ discussions</span>
            </div>
          </div>
        </div>

        <div className="auth-proof">
          <div><MessageCircleMore size={18} /> Real discussions</div>
          <div><BookOpen size={18} /> Expert context</div>
          <div><BarChart3 size={18} /> Price signals</div>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-panel__mobile-logo"><Logo /></div>
        <div className="auth-card">
          <span className="eyebrow">{mode === "login" ? "Welcome back" : "Join Rekomme"}</span>
          <h2>{mode === "login" ? "Shop with more confidence." : "Create your account."}</h2>
          <p className="auth-card__intro">
            {mode === "login"
              ? "Your next shortlist is a conversation away."
              : "Save conversations and build smarter shortlists."}
          </p>

          <div className="auth-tabs" role="tablist" aria-label="Account action">
            <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")} type="button">Sign in</button>
            <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")} type="button">Create account</button>
          </div>

          <form onSubmit={submit} className="auth-form">
            <label>
              Username
              <input name="username" value={form.username} onChange={update} autoComplete="username" placeholder="Your username" />
            </label>

            {mode === "register" && (
              <div className="field-grid">
                <label>
                  Email
                  <input name="email" type="email" value={form.email} onChange={update} autoComplete="email" placeholder="you@example.com" />
                </label>
                <label>
                  Full name
                  <input name="full_name" value={form.full_name} onChange={update} autoComplete="name" placeholder="Optional" />
                </label>
              </div>
            )}

            <label>
              Password
              <input name="password" type="password" value={form.password} onChange={update} autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder="••••••••" />
            </label>

            {error && <div className="form-message form-message--error">{error}</div>}
            {notice && <div className="form-message form-message--success">{notice}</div>}

            <button className="button button--primary button--full" disabled={busy}>
              {busy ? <span className="spinner" /> : mode === "login" ? "Start exploring" : "Create my account"}
              {!busy && <ArrowRight size={18} />}
            </button>
          </form>

          {mode === "login" && (
            <button className="demo-access" onClick={useDemo} type="button">
              <span><CircleUserRound size={18} /> Reviewing the demo?</span>
              <strong>Use demo access <ArrowRight size={15} /></strong>
            </button>
          )}
        </div>
        <p className="auth-legal">Recommendations are AI-assisted. Verify specifications and prices with the retailer.</p>
      </section>
    </main>
  );
}

function Sidebar({
  open,
  onClose,
  sessions,
  activeSession,
  onSession,
  onNewChat,
  category,
  categories,
  onCategory,
  onLogout
}) {
  return (
    <>
      <button className={`sidebar-scrim ${open ? "visible" : ""}`} onClick={onClose} aria-label="Close navigation" />
      <aside className={`sidebar ${open ? "sidebar--open" : ""}`}>
        <div className="sidebar__head">
          <Logo />
          <button className="icon-button sidebar__close" onClick={onClose} aria-label="Close menu"><X size={20} /></button>
        </div>

        <button className="new-chat" onClick={onNewChat}>
          <Plus size={17} /> New discovery
          <span>⌘ K</span>
        </button>

        <div className="category-picker">
          <label htmlFor="category">Shopping for</label>
          <div className="select-wrap">
            <ShoppingBag size={17} />
            <select id="category" value={category} onChange={(event) => onCategory(event.target.value)}>
              {categories.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <ChevronDown size={16} />
          </div>
        </div>

        <nav className="recent-chats" aria-label="Recent chats">
          <div className="sidebar-label"><span>Recent discoveries</span><Clock3 size={14} /></div>
          <div className="recent-chats__list">
            {sessions.length === 0 && <p className="sidebar-empty">Your saved conversations will show up here.</p>}
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => onSession(session.id)}
                className={String(activeSession) === String(session.id) ? "active" : ""}
              >
                <MessageSquareText size={16} />
                <span>{session.title || "Untitled discovery"}</span>
              </button>
            ))}
          </div>
        </nav>

        <div className="sidebar__footer">
          <div className="profile-chip">
            <span>{authStore.username().slice(0, 1).toUpperCase()}</span>
            <div><strong>{authStore.username()}</strong><small>Thoughtful shopper</small></div>
          </div>
          <button className="icon-button icon-button--dark" onClick={onLogout} aria-label="Sign out"><LogOut size={18} /></button>
        </div>
      </aside>
    </>
  );
}

function EmptyState({ onExample }) {
  return (
    <section className="empty-state">
      <div className="empty-state__copy">
        <span className="eyebrow"><span className="status-dot" /> Powered by real owner experience</span>
        <h1>What are you hoping<br />to bring home?</h1>
        <p>Describe what matters—budget, use case, dealbreakers. We’ll turn the internet’s noise into a shortlist worth considering.</p>
      </div>

      <div className="example-grid">
        {EXAMPLES.map(({ label, query, icon: Icon }, index) => (
          <button key={query} onClick={() => onExample(query)} style={{ "--delay": `${index * 55}ms` }}>
            <span className="example-grid__icon"><Icon size={19} /></span>
            <span><small>{label}</small><strong>{query}</strong></span>
            <ArrowRight size={17} />
          </button>
        ))}
      </div>

      <div className="method-strip">
        <span><UsersRound size={17} /> Community-backed</span>
        <i />
        <span><BadgeCheck size={17} /> Cross-checked</span>
        <i />
        <span><Tag size={17} /> Price-aware</span>
      </div>
    </section>
  );
}

function Markdown({ children }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
      a: ({ ...props }) => <a {...props} target="_blank" rel="noreferrer" />
    }}>
      {children || ""}
    </ReactMarkdown>
  );
}

function SourceLink({ href, children, tone = "neutral", icon: Icon = ExternalLink }) {
  if (!href) return null;
  return (
    <a className={`source-link source-link--${tone}`} href={href} target="_blank" rel="noreferrer">
      <Icon size={14} /> <span>{children}</span> <ExternalLink size={12} />
    </a>
  );
}

function ProductCard({ product, index, listings = [], selected, onToggle }) {
  const pricing = product.pricing_insight || {};
  const trend = (pricing.price_trend || "").toLowerCase();
  const searchUrl = `https://www.google.com/search?tbm=shop&q=${encodeURIComponent(product.product_name || "")}`;
  const community = product.community_sources || [];
  const news = product.news_articles || [];
  const videos = product.youtube_reviews || [];

  return (
    <article className={`product-card ${selected ? "product-card--selected" : ""}`}>
      <div className="product-card__topline">
        <span className="rank">#{String(index + 1).padStart(2, "0")}</span>
        <button className="select-product" onClick={onToggle} aria-pressed={selected}>
          <span>{selected && <Check size={13} />}</span>{selected ? "Selected" : "Select"}
        </button>
      </div>

      <div className="product-card__title">
        <h3>{product.product_name}</h3>
        {pricing.lowest_price && <strong>{pricing.lowest_price}</strong>}
      </div>
      <p className="recommendation-reason">{product.reason_for_recommendation}</p>

      {(trend || pricing.best_time_to_buy) && (
        <div className={`price-signal price-signal--${trend === "dropping" ? "good" : trend === "rising" ? "warn" : "steady"}`}>
          {trend === "dropping" ? <TrendingDown size={17} /> : trend === "rising" ? <TrendingUp size={17} /> : <BarChart3 size={17} />}
          <div><span>{trend ? `${trend} price trend` : "Price signal"}</span><strong>{pricing.best_time_to_buy || "Prices look stable right now."}</strong></div>
        </div>
      )}

      <div className="product-card__section">
        <div className="section-label"><MessageCircleMore size={15} /> What owners say</div>
        <div className="review-copy"><Markdown>{product.detailed_review || product.reason_for_recommendation}</Markdown></div>
      </div>

      <div className="product-card__section">
        <div className="section-label"><ShoppingBag size={15} /> Where to shop</div>
        <div className="merchant-list">
          {listings.slice(0, 3).map((listing, listingIndex) => (
            <a key={`${listing.product_url}-${listingIndex}`} href={listing.product_url} target="_blank" rel="noreferrer">
              <span><small>{listing.merchant_name || "Retailer"}</small><strong>{listing.title || product.product_name}</strong></span>
              <b>{listing.price || "View"}</b>
            </a>
          ))}
          {listings.length === 0 && (
            <a href={searchUrl} target="_blank" rel="noreferrer" className="merchant-list__fallback">
              <span><small>Live listings unavailable</small><strong>Compare current offers</strong></span>
              <ArrowRight size={16} />
            </a>
          )}
        </div>
      </div>

      {(community.length > 0 || news.length > 0 || videos.length > 0) && (
        <div className="product-card__section product-card__sources">
          <div className="section-label"><Layers3 size={15} /> Evidence trail</div>
          <div className="source-stack">
            {community.slice(0, 2).map((source, sourceIndex) => (
              <SourceLink key={`${source.url}-${sourceIndex}`} href={source.url} tone="community" icon={MessageCircleMore}>
                {source.title || (source.subreddit ? `r/${source.subreddit}` : "Community discussion")}
              </SourceLink>
            ))}
            {news.slice(0, 2).map((article, articleIndex) => (
              <SourceLink key={`${article.url}-${articleIndex}`} href={article.url} icon={BookOpen}>
                {article.title || article.source || "Expert review"}
              </SourceLink>
            ))}
            {videos.slice(0, 1).map((video, videoIndex) => (
              <SourceLink key={`${video.url}-${videoIndex}`} href={video.url} tone="video" icon={Video}>
                {video.title || "Video review"}
              </SourceLink>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}

function ProductResults({ message, selected, onToggle, onAction }) {
  return (
    <div className="results-block">
      <div className="insight-note">
        <span><Sparkles size={16} /></span>
        <div><small>Why these made the cut</small><p>{message.summary || "These options best match the priorities in your request."}</p></div>
      </div>
      <div className="product-grid">
        {message.products.map((product, index) => (
          <ProductCard
            key={`${product.product_name}-${index}`}
            product={product}
            index={index}
            listings={message.listings?.[product.product_name] || []}
            selected={selected.has(product.product_name)}
            onToggle={() => onToggle(product.product_name)}
          />
        ))}
      </div>
      {selected.size > 0 && (
        <div className="selection-bar">
          <div><span>{selected.size}</span><p><strong>On your shortlist</strong><small>Select another to compare side by side.</small></p></div>
          <div className="selection-bar__actions">
            <button className="button button--secondary" onClick={() => onAction("details")}>Deep dive</button>
            <button className="button button--primary" disabled={selected.size < 2} onClick={() => onAction("compare")}>Compare picks</button>
          </div>
        </div>
      )}
    </div>
  );
}

function Message({ message, isLatestResults, selected, onToggle, onAction }) {
  if (message.role === "user") {
    return <div className="message message--user"><div>{message.content}</div></div>;
  }

  return (
    <div className="message message--assistant">
      <div className="assistant-mark"><Sparkles size={16} /></div>
      <div className="assistant-content">
        {message.products?.length ? (
          <ProductResults
            message={message}
            selected={isLatestResults ? selected : new Set()}
            onToggle={isLatestResults ? onToggle : () => {}}
            onAction={onAction}
          />
        ) : (
          <div className="markdown-response"><Markdown>{message.content}</Markdown></div>
        )}
      </div>
    </div>
  );
}

function ThinkingState({ followUp }) {
  const steps = followUp
    ? ["Reviewing your shortlist", "Weighing the tradeoffs", "Writing a clear answer"]
    : ["Reading owner discussions", "Cross-checking expert context", "Building your shortlist"];
  return (
    <div className="thinking-state">
      <div className="thinking-orbit"><Sparkles size={18} /></div>
      <div><strong>{followUp ? "Looking closer…" : "Searching with intent…"}</strong><span>{steps.join("  ·  ")}</span></div>
    </div>
  );
}

function Composer({ value, onChange, onSubmit, disabled, compact }) {
  const ref = useRef(null);
  const submit = (event) => {
    event?.preventDefault();
    if (value.trim() && !disabled) onSubmit(value.trim());
  };

  const onKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.height = "auto";
    ref.current.style.height = `${Math.min(ref.current.scrollHeight, 132)}px`;
  }, [value]);

  return (
    <form className={`composer ${compact ? "composer--compact" : ""}`} onSubmit={submit}>
      <Search size={19} />
      <textarea
        ref={ref}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Tell me what you’re shopping for, your budget, and what matters most…"
        rows={1}
        disabled={disabled}
        aria-label="Ask Rekomme"
      />
      <button type="submit" disabled={!value.trim() || disabled} aria-label="Send message"><Send size={18} /></button>
    </form>
  );
}

function parseStoredMessage(message) {
  const role = message.role === "system" ? "assistant" : "user";
  if (role === "assistant") {
    try {
      const parsed = JSON.parse(message.content);
      if (parsed.products?.length) {
        return { role, products: parsed.products, summary: parsed.reasoning_summary || "", listings: {} };
      }
    } catch {
      // Stored follow-up answers are plain markdown.
    }
  }
  return { role, content: message.content };
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(authStore.access()));
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [categories, setCategories] = useState(["headphones", "sneakers"]);
  const [category, setCategory] = useState("headphones");
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [recommendedProducts, setRecommendedProducts] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingFollowUp, setLoadingFollowUp] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  const refreshSessions = async () => {
    const payload = await api.sessions();
    const normalized = Object.entries(payload)
      .map(([id, title]) => ({ id: Number(id), title }))
      .sort((a, b) => b.id - a.id);
    setSessions(normalized);
  };

  useEffect(() => {
    if (!authenticated) return;
    let active = true;
    Promise.all([api.categories(), api.sessions()])
      .then(([categoryData, sessionData]) => {
        if (!active) return;
        if (categoryData.choices?.length) {
          setCategories(categoryData.choices);
          setCategory(categoryData.choices[0]);
        }
        setSessions(
          Object.entries(sessionData)
            .map(([id, title]) => ({ id: Number(id), title }))
            .sort((a, b) => b.id - a.id)
        );
      })
      .catch((err) => {
        if (!authStore.access()) setAuthenticated(false);
        else setError(err.message);
      });
    return () => { active = false; };
  }, [authenticated]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const fetchListings = async (products) => {
    const entries = await Promise.all(
      products.map(async (product) => {
        try {
          const listings = await api.listings(product.product_name);
          return [product.product_name, Array.isArray(listings) ? listings.slice(0, 3) : []];
        } catch {
          return [product.product_name, []];
        }
      })
    );
    return Object.fromEntries(entries);
  };

  const loadSession = async (sessionId) => {
    setSidebarOpen(false);
    setError("");
    setLoading(true);
    try {
      const stored = await api.messages(sessionId);
      const parsed = stored.map(parseStoredMessage);
      let lastProducts = [];
      for (const message of parsed) {
        if (message.products?.length) lastProducts = message.products;
      }
      if (lastProducts.length) {
        const listings = await fetchListings(lastProducts);
        for (let index = parsed.length - 1; index >= 0; index -= 1) {
          if (parsed[index].products?.length) {
            parsed[index] = { ...parsed[index], listings };
            break;
          }
        }
      }
      setMessages(parsed);
      setRecommendedProducts(lastProducts);
      setSelected(new Set());
      setActiveSession(sessionId);
    } catch (err) {
      setError(err.message || "Could not load that conversation.");
    } finally {
      setLoading(false);
    }
  };

  const newChat = () => {
    setMessages([]);
    setRecommendedProducts([]);
    setSelected(new Set());
    setActiveSession(null);
    setError("");
    setSidebarOpen(false);
  };

  const sendPrompt = async (prompt, forcedType = null, forcedProducts = null) => {
    if (!prompt || loading) return;
    const contextProducts = forcedProducts || recommendedProducts;
    const followUp = Boolean(forcedType || (contextProducts.length && isFollowUpQuery(prompt)));
    setDraft("");
    setError("");
    setLoading(true);
    setLoadingFollowUp(followUp);
    setMessages((current) => [...current, { role: "user", content: prompt }]);

    try {
      if (followUp) {
        const response = await api.followUp({
          prompt,
          products_context: contextProducts,
          chat_session_id: activeSession,
          follow_up_type: forcedType || "question"
        });
        setActiveSession(response.chat_session_id || activeSession);
        setMessages((current) => [...current, { role: "assistant", content: response.response }]);
      } else {
        const response = await api.initialSearch({
          model: "gpt-4o-mini",
          prompt,
          category,
          chat_session_id: activeSession
        });
        const products = response.response?.products || [];
        const listings = products.length ? await fetchListings(products) : {};
        setActiveSession(response.chat_session_id);
        setRecommendedProducts(products);
        setSelected(new Set());
        setMessages((current) => [
          ...current,
          products.length
            ? { role: "assistant", products, listings, summary: response.response?.reasoning_summary || "" }
            : { role: "assistant", content: "I couldn’t find a strong match yet. Try adding a budget, use case, or a must-have feature." }
        ]);
      }
      await refreshSessions();
    } catch (err) {
      setError(err.message || "The search hit a snag. Please try again.");
    } finally {
      setLoading(false);
      setLoadingFollowUp(false);
    }
  };

  const toggleSelected = (name) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const selectionAction = (type) => {
    const products = recommendedProducts.filter((product) => selected.has(product.product_name));
    if (!products.length) return;
    const names = products.map((product) => product.product_name).join(", ");
    const prompt = type === "compare"
      ? `Compare these products side by side: ${names}`
      : `Give me a detailed buyer's guide for: ${names}`;
    sendPrompt(prompt, type, products);
  };

  const logout = () => {
    authStore.clear();
    setAuthenticated(false);
    newChat();
  };

  const latestResultsIndex = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].products?.length) return index;
    }
    return -1;
  }, [messages]);

  if (!authenticated) return <AuthScreen onAuthenticated={() => setAuthenticated(true)} />;

  return (
    <div className="app-shell">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sessions={sessions}
        activeSession={activeSession}
        onSession={loadSession}
        onNewChat={newChat}
        category={category}
        categories={categories}
        onCategory={setCategory}
        onLogout={logout}
      />

      <main className="workspace">
        <header className="workspace-header">
          <button className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={21} /></button>
          <div className="workspace-header__title">
            <span className="mobile-logo"><Logo compact /></span>
            <div><strong>{activeSession ? "Your discovery" : "Discovery desk"}</strong><small>Community insight, minus the rabbit holes</small></div>
          </div>
          <div className="workspace-header__meta">
            <span><span className="status-dot" /> Sources online</span>
            <button className="profile-button" title={authStore.username()}>{authStore.username().slice(0, 1).toUpperCase()}</button>
          </div>
        </header>

        <div className={`conversation ${messages.length ? "conversation--active" : ""}`}>
          {!messages.length && !loading ? (
            <>
              <EmptyState onExample={(query) => { setDraft(query); sendPrompt(query); }} />
              <div className="composer-dock composer-dock--hero">
                <Composer value={draft} onChange={setDraft} onSubmit={sendPrompt} disabled={loading} />
                <p><span>↵</span> to send <i /> <span>⇧ ↵</span> for a new line</p>
              </div>
            </>
          ) : (
            <div className="conversation__inner">
              <div className="conversation-heading">
                <span className="eyebrow">Live recommendation workspace</span>
                <h1>Let’s narrow it down.</h1>
              </div>

              {messages.map((message, index) => (
                <Message
                  key={`${index}-${message.role}`}
                  message={message}
                  isLatestResults={index === latestResultsIndex}
                  selected={selected}
                  onToggle={toggleSelected}
                  onAction={selectionAction}
                />
              ))}
              {loading && <ThinkingState followUp={loadingFollowUp} />}
              {error && <div className="error-banner"><span>!</span><p>{error}</p><button onClick={() => setError("")}><X size={16} /></button></div>}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {messages.length > 0 && (
          <div className="composer-dock composer-dock--sticky">
            <Composer value={draft} onChange={setDraft} onSubmit={sendPrompt} disabled={loading} compact />
            <p>Ask a follow-up, change the budget, or start a new comparison.</p>
          </div>
        )}
      </main>
    </div>
  );
}
