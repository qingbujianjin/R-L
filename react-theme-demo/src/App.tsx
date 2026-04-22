import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ThemeProvider, useTheme } from "./ThemeContext";
import { THEME_ORDER, THEMES } from "./themes";

function ThemeShowcase() {
  const { themeId, setThemeId, theme, cycleTheme } = useTheme();
  const reduceMotion = useReducedMotion();

  const pageMotion = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.2 } }
    : theme.animation.page;

  return (
    <main className="min-h-screen px-6 py-8 md:px-10">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="kicker">Literary Easter Theme System</p>
            <h1 className="display-title">情绪不是颜色，而是叙事接口</h1>
          </div>
          <div className="flex items-center gap-3">
            <select
              className="theme-select"
              value={themeId}
              onChange={(e) => setThemeId(e.target.value as keyof typeof THEMES)}
              aria-label="切换文学主题"
            >
              {THEME_ORDER.map((id) => (
                <option key={id} value={id}>
                  {THEMES[id].name}
                </option>
              ))}
            </select>
            <button className="theme-btn theme-btn-primary" onClick={cycleTheme}>
              下一章
            </button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          <motion.section
            key={themeId}
            initial={pageMotion.initial}
            animate={pageMotion.animate}
            transition={pageMotion.transition}
            className={`showcase-grid ${themeId === "aleph" ? "aleph-layout" : ""}`}
          >
            <motion.article
              className="theme-card"
              whileHover={reduceMotion ? undefined : theme.animation.card.whileHover}
            >
              <h2 className="card-title">{theme.name}</h2>
              <p className="card-body">
                这是一个可切换的文学主题样板。你可以把它接到仪表盘、播放器、阅读器或任何需要情绪化视觉语言的产品。
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <button className="theme-btn theme-btn-primary">主要操作</button>
                <button className="theme-btn theme-btn-secondary">次要操作</button>
              </div>
            </motion.article>

            <motion.article
              className="theme-card collage"
              whileHover={reduceMotion ? undefined : theme.animation.card.whileHover}
            >
              <h3 className="card-title text-2xl">微交互说明</h3>
              <ul className="list space-y-2">
                <li>主题切换触发过渡动画与变量重映射</li>
                <li>控制台自动输出文学梗彩蛋</li>
                <li>不同主题自动切换边框、阴影、圆角与噪点强度</li>
              </ul>
            </motion.article>

            <motion.article
              className={`theme-card empty-state ${themeId === "outsider" ? "outsider-empty" : ""}`}
              whileHover={reduceMotion ? undefined : theme.animation.card.whileHover}
            >
              <h3 className="card-title text-2xl">空状态</h3>
              {themeId === "outsider" ? (
                <div className="matchman" aria-label="局外人主题空状态火柴人">
                  <span className="head" />
                  <span className="body" />
                  <span className="arm left" />
                  <span className="arm right" />
                  <span className="leg left" />
                  <span className="leg right" />
                </div>
              ) : (
                <p className="card-body">暂无数据。这里可用于播放器队列、统计图或推荐内容占位。</p>
              )}
            </motion.article>
          </motion.section>
        </AnimatePresence>
      </div>
    </main>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <ThemeShowcase />
    </ThemeProvider>
  );
}
