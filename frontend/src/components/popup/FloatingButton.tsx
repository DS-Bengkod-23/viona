"use client"

import React from "react"
import { motion, AnimatePresence } from "motion/react"

interface FloatingButtonProps {
  onClick: () => void
  isOpen: boolean
}

export function FloatingButton({ onClick, isOpen }: FloatingButtonProps) {
  return (
    <AnimatePresence>
      {!isOpen && (
        <>
          <style>{`
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@700&display=swap');

            @keyframes vionaGlow {
              0%, 100% { box-shadow: 0 0 15px rgba(124, 58, 237, 0.4), 0 0 30px rgba(124, 58, 237, 0.2); }
              50% { box-shadow: 0 0 25px rgba(124, 58, 237, 0.6), 0 0 50px rgba(124, 58, 237, 0.35); }
            }
            @keyframes vionaFloat {
              0%, 100% { transform: translateY(0); }
              50% { transform: translateY(-6px); }
            }
            @keyframes vionaWave {
              0%, 100% { transform: rotate(0deg); }
              25% { transform: rotate(12deg); }
              50% { transform: rotate(-6deg); }
              75% { transform: rotate(12deg); }
            }
            #viona-floating-icon { animation: vionaFloat 3s ease-in-out infinite; }
            #viona-floating-icon:hover .viona-btn { transform: scale(1.05); }
            .viona-arm-left { animation: vionaWave 2.5s ease-in-out infinite 0.3s; transform-origin: right center; }
            .viona-arm-right { animation: vionaWave 2.5s ease-in-out infinite; transform-origin: left center; }
          `}</style>

          <motion.button
            type="button"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            onClick={onClick}
            id="viona-floating-icon"
            aria-label="Buka chat Viona"
            className="fixed bottom-6 right-8 z-50"
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              cursor: "pointer",
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              background: "transparent",
              border: "none",
              padding: 0,
            }}
          >
          <div style={{ transform: "scale(0.72)", transformOrigin: "bottom right", display: "flex", flexDirection: "column", alignItems: "center" }}>
            {/* Karakter Blob Organik */}
            <div style={{ position: "relative", width: 130, height: 140 }}>
              {/* Body blob */}
              <div
                style={{
                  width: 120,
                  height: 120,
                  background: "linear-gradient(160deg, #A78BFA 0%, #7C3AED 35%, #6D28D9 70%, #5B21B6 100%)",
                  borderRadius: "60% 40% 50% 50% / 50% 60% 40% 50%",
                  position: "relative",
                  boxShadow: "0 8px 24px rgba(109, 40, 217, 0.3), inset 0 3px 8px rgba(255,255,255,0.2)",
                  margin: "10px auto 0",
                }}
              >
                {/* Highlight */}
                <div
                  style={{
                    position: "absolute",
                    top: 8,
                    left: 12,
                    width: 40,
                    height: 30,
                    background: "radial-gradient(ellipse, rgba(255,255,255,0.25), transparent)",
                    borderRadius: "50%",
                    transform: "rotate(-20deg)",
                  }}
                />

                {/* Left eye */}
                <div style={{ position: "absolute", top: 30, left: 22, zIndex: 2 }}>
                  <div
                    style={{
                      width: 20,
                      height: 22,
                      background: "white",
                      borderRadius: "50%",
                      boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        top: 5,
                        left: 5,
                        width: 11,
                        height: 12,
                        background: "radial-gradient(circle at 40% 40%, #1E1B4B 60%, #312E81 100%)",
                        borderRadius: "50%",
                      }}
                    />
                    <div
                      style={{
                        position: "absolute",
                        top: 6,
                        left: 8,
                        width: 4,
                        height: 4,
                        background: "white",
                        borderRadius: "50%",
                      }}
                    />
                  </div>
                </div>

                {/* Right eye */}
                <div style={{ position: "absolute", top: 30, right: 22, zIndex: 2 }}>
                  <div
                    style={{
                      width: 20,
                      height: 22,
                      background: "white",
                      borderRadius: "50%",
                      boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        top: 5,
                        left: 5,
                        width: 11,
                        height: 12,
                        background: "radial-gradient(circle at 40% 40%, #1E1B4B 60%, #312E81 100%)",
                        borderRadius: "50%",
                      }}
                    />
                    <div
                      style={{
                        position: "absolute",
                        top: 6,
                        left: 8,
                        width: 4,
                        height: 4,
                        background: "white",
                        borderRadius: "50%",
                      }}
                    />
                  </div>
                </div>

                {/* Mouth */}
                <div style={{ position: "absolute", bottom: 24, left: "50%", transform: "translateX(-50%)", zIndex: 2 }}>
                  <div
                    style={{
                      width: 30,
                      height: 16,
                      background: "#4C1D95",
                      borderRadius: "0 0 50% 50%",
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        bottom: -2,
                        left: "50%",
                        transform: "translateX(-50%)",
                        width: 14,
                        height: 10,
                        background: "linear-gradient(180deg, #F87171, #EF4444)",
                        borderRadius: "50%",
                      }}
                    />
                  </div>
                </div>

                {/* Blush */}
                <div
                  style={{
                    position: "absolute",
                    top: 54,
                    left: 10,
                    width: 18,
                    height: 10,
                    background: "radial-gradient(ellipse, rgba(248, 140, 200, 0.3), transparent)",
                    borderRadius: "50%",
                    zIndex: 2,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: 54,
                    right: 10,
                    width: 18,
                    height: 10,
                    background: "radial-gradient(ellipse, rgba(248, 140, 200, 0.3), transparent)",
                    borderRadius: "50%",
                    zIndex: 2,
                  }}
                />
              </div>

              {/* Graduation cap */}
              <div style={{ position: "absolute", top: -6, left: "50%", transform: "translateX(-50%) rotate(-8deg)", zIndex: 3 }}>
                <div
                  style={{
                    width: 56,
                    height: 12,
                    background: "linear-gradient(135deg, #312E81, #1E1B4B)",
                    borderRadius: 3,
                    boxShadow: "0 3px 8px rgba(0,0,0,0.2)",
                    position: "relative",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      top: -3,
                      left: "50%",
                      transform: "translateX(-50%)",
                      width: 8,
                      height: 6,
                      background: "linear-gradient(135deg, #EAB308, #F59E0B)",
                      borderRadius: "50%",
                    }}
                  />
                </div>
                <div
                  style={{
                    width: 36,
                    height: 16,
                    background: "linear-gradient(180deg, #3730A3, #312E81)",
                    borderRadius: "0 0 6px 6px",
                    margin: "-2px auto 0",
                    boxShadow: "inset 0 -2px 4px rgba(0,0,0,0.15)",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: 6,
                    right: -6,
                    width: 2,
                    height: 22,
                    background: "linear-gradient(180deg, #EAB308, #D97706)",
                    borderRadius: 1,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: 26,
                    right: -10,
                    width: 10,
                    height: 10,
                    background: "radial-gradient(circle, #F59E0B, #EAB308)",
                    borderRadius: "50%",
                    boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
                  }}
                />
              </div>

              {/* Arms */}
              <div className="viona-arm-left" style={{ position: "absolute", top: 80, left: -14, zIndex: 1 }}>
                <div
                  style={{
                    width: 22,
                    height: 16,
                    background: "linear-gradient(135deg, #A78BFA, #8B5CF6)",
                    borderRadius: "12px 4px 4px 12px",
                    boxShadow: "0 2px 4px rgba(109, 40, 217, 0.2)",
                  }}
                />
              </div>
              <div className="viona-arm-right" style={{ position: "absolute", top: 80, right: -14, zIndex: 1 }}>
                <div
                  style={{
                    width: 22,
                    height: 16,
                    background: "linear-gradient(225deg, #A78BFA, #8B5CF6)",
                    borderRadius: "4px 12px 12px 4px",
                    boxShadow: "0 2px 4px rgba(109, 40, 217, 0.2)",
                  }}
                />
              </div>

              {/* Book badge */}
              <div
                style={{
                  position: "absolute",
                  bottom: 4,
                  right: -8,
                  background: "white",
                  borderRadius: 10,
                  width: 32,
                  height: 28,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 3px 10px rgba(79, 70, 229, 0.25)",
                  zIndex: 4,
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#7C3AED" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                </svg>
              </div>

              {/* Sparkles */}
              <div style={{ position: "absolute", top: -4, right: -20, zIndex: 4 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="#C4B5FD"><path d="M12 0L14.5 9.5L24 12L14.5 14.5L12 24L9.5 14.5L0 12L9.5 9.5L12 0Z"></path></svg>
              </div>
              <div style={{ position: "absolute", bottom: 20, left: -24, zIndex: 4 }}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="#DDD6FE"><path d="M12 0L14.5 9.5L24 12L14.5 14.5L12 24L9.5 14.5L0 12L9.5 9.5L12 0Z"></path></svg>
              </div>
            </div>

            {/* Label button */}
            <div
              className="viona-btn"
              style={{
                background: "linear-gradient(135deg, #7C3AED 0%, #6D28D9 50%, #4F46E5 100%)",
                color: "white",
                padding: "11px 30px",
                borderRadius: 30,
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 700,
                fontSize: 14,
                display: "flex",
                alignItems: "center",
                gap: 8,
                animation: "vionaGlow 2s ease-in-out infinite",
                marginTop: 8,
                boxShadow: "0 4px 16px rgba(109, 40, 217, 0.35)",
                transition: "transform 0.2s",
                whiteSpace: "nowrap",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              Tanya Viona
            </div>
          </div>
          </motion.button>
        </>
      )}
    </AnimatePresence>
  )
}
